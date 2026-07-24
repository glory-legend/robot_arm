#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""학습형 파지 선택기 (GraspSelector) — ROS 무의존 순수 numpy/sklearn/json 모듈.

메인 빈피킹 노드(franka_integrated_pick_place.py)가 '어느 볼트를, 어느 접근각으로'
집을지 고르는 판단을 온라인 학습으로 대체하기 위한 분류기다.

[왜 ROS 를 안 쓰나]
  rclpy 임포트는 WSL 에서 ROS 환경 소싱이 필요해 단독 테스트가 번거롭다. 특징
  계산(레이캐스트/이웃거리 등)은 이미 메인 노드가 기하학적으로 다 하므로, 여기서는
  '특징 dict → 정렬 벡터 변환 + 학습/추론'만 담당한다. 덕분에 이 파일은 numpy/
  sklearn/json 만으로 단독 실행·검증할 수 있다.

[왜 SGDClassifier(log_loss) 인가]
  매 파지 시도가 라벨 1개(성공/실패)씩 실시간으로 들어오는 스트리밍 환경이다.
  SGDClassifier 는 partial_fit 으로 표본 1개씩 온라인 갱신이 가능해, "시뮬 한 번
  돌 때마다 조금씩 똑똑해지는" 지속 학습에 정확히 맞는다. loss='log_loss' 는
  로지스틱 회귀와 동치라 predict_proba(성공 확률)를 그대로 얻는다. StandardScaler
  역시 partial_fit 을 지원하므로 스케일도 온라인으로 함께 추정한다.

[콜드 스타트 / 탐험]
  표본이 적거나 한쪽 클래스(전부 성공 또는 전부 실패)뿐이면 확률 추정이 무의미
  하므로 ready()=False → 호출측이 기존 휴리스틱(_select_topmost_bolt)으로 폴백한다.
  또한 최고점만 계속 고르면 '한 번도 시도 안 해 본 자세'의 데이터가 영원히 안
  모이는 선택 편향이 생긴다 → ε-탐험으로 초반에는 차선 후보도 일부러 섞는다.
"""

import json
import math
import os
import pickle

import numpy as np

# sklearn 임포트가 실패하면(미설치 등) 선택기 전체를 조용히 비활성화한다.
# 메인 노드는 available=False 를 보고 기존 휴리스틱으로만 동작하므로, 학습
# 스택이 없어도 데모 자체는 절대 죽지 않는다.
try:
    from sklearn.linear_model import SGDClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.utils.class_weight import compute_class_weight
    _SKLEARN_OK = True
    _SKLEARN_ERR = ''
except Exception as exc:                       # noqa: BLE001 (어떤 임포트 실패도 흡수)
    SGDClassifier = None
    StandardScaler = None
    compute_class_weight = None
    _SKLEARN_OK = False
    _SKLEARN_ERR = repr(exc)


# ---------------------------------------------------------------------------
# 특징 순서(모듈 상수) — 학습·추론·저장 전 구간에서 이 순서가 유일한 진실이다.
# 메인 노드는 dict 로 특징을 넘기고, 여기서 이 순서대로 벡터화한다. dict 라
# 순서 실수로 열이 뒤섞이는 사고를 원천 차단한다.
#   z         : 볼트 중심 높이(m) — 위에 얹힌 볼트일수록 집기 쉽다
#   clear     : 최근접 이웃까지 xy 거리(m) — 붐빌수록 손가락 간섭 위험
#   n_neigh   : 반경 0.09 내 이웃 수 — 무더기 밀집도
#   aperture  : 계산된 실현 개구(m) — 좁을수록 여유 부족
#   wall_cap  : 벽 제약 상한 개구(m)
#   ap_at_min : 개구가 하한(GRASP_MIN_OPEN)까지 눌렸나 0/1 — 한계 파지 신호
#   tilt      : 접근 기울기(deg) — 0=수직, 크면 벽 회피용 경사
#   wall_reach: 손가락 방향 벽까지 최소 경로거리(m). inf 는 0.5 로 클립
#   axis_vert : 볼트 축의 |z 성분| — 1 에 가까우면 세워진 볼트(옆파지 난이도↑)
#   reach     : sqrt(tx²+ty²) — 로봇 기준 수평 도달거리(관절 한계 근접도 대용)
#   tx, ty    : 파지점 xy(로봇 기준) — 작업공간 위치 편향 학습용
# ---------------------------------------------------------------------------
FEATURES = [
    'z', 'clear', 'n_neigh', 'aperture', 'wall_cap', 'ap_at_min',
    'tilt', 'wall_reach', 'axis_vert', 'reach', 'tx', 'ty',
]

# wall_reach 가 inf(벽에 막히지 않음)일 때 대입할 유한 상수. 통 내부 최대 도달이
# 0.2m 안팎이라 0.5 면 '사실상 벽 제약 없음'을 뜻하는 충분히 큰 유한값이다.
_WALL_REACH_INF_CLIP = 0.5

# 콜드 스타트 기준: 이 표본 수 미만이거나 한쪽 클래스뿐이면 아직 신뢰 불가.
_MIN_SAMPLES_READY = 30

# ε-탐험 스케줄 파라미터.
_EPS_START = 0.20        # 표본 0 개일 때 탐험 확률
_EPS_END = 0.05          # 충분히 모였을 때 최저 탐험 확률
_EPS_DECAY_N = 300       # 이 표본 수까지 선형 감소 후 하한 유지


def feat_to_vector(feat):
    """특징 dict → FEATURES 순서의 1차원 float ndarray.

    누락 키는 0.0 으로, wall_reach 의 inf/NaN 은 유한값으로 안전 변환한다.
    (특징 계산 주체는 메인 노드지만, 방어적으로 여기서도 결측/무한을 흡수한다.)
    """
    vec = np.zeros(len(FEATURES), dtype=float)
    for i, name in enumerate(FEATURES):
        v = feat.get(name, 0.0)
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = 0.0
        if name == 'wall_reach' and (not math.isfinite(v)):
            v = _WALL_REACH_INF_CLIP
        elif not math.isfinite(v):
            v = 0.0
        if name == 'wall_reach':
            v = min(v, _WALL_REACH_INF_CLIP)
        vec[i] = v
    return vec


class GraspSelector:
    """온라인 학습형 파지 성공확률 예측기.

    표본이 충분(양쪽 클래스 ≥ _MIN_SAMPLES_READY)해지면 ready()=True 가 되고,
    그때부터 메인 노드가 predict_proba 로 후보를 랭킹한다. 그 전에는 조용히
    비활성 상태로 남아 호출측이 휴리스틱으로 폴백한다.
    """

    def __init__(self):
        self.available = _SKLEARN_OK
        self.sklearn_error = _SKLEARN_ERR
        # partial_fit 이 한 번이라도 성공적으로 호출됐는지(추론 가능 여부).
        self._fitted = False
        self.n_samples = 0
        # 지금까지 실제로 관측한 클래스 집합 — ready() 의 '양쪽 클래스 존재' 판정용.
        self._classes_seen = set()
        # 최근 표본을 메모리에 누적(전체 재적합/디버깅용). jsonl 이 영속 저장소이고
        # 이 버퍼는 휘발성 보조라, 무한정 커지지 않게 상한을 둔다.
        self._buf_X = []
        self._buf_y = []
        self._buf_cap = 5000
        if self.available:
            self._new_model()
        else:
            self.scaler = None
            self.clf = None

    # ----- 내부 유틸 -----
    def _new_model(self):
        """새 StandardScaler + SGDClassifier(log_loss) 쌍을 만든다(warm_start 초기화)."""
        self.scaler = StandardScaler()
        # alpha: L2 정규화 강도. 표본이 적은 초반 과적합을 억제하는 완만한 기본값.
        # class_weight: partial_fit 은 'balanced' 문자열을 못 받으므로(정의상 전체
        #   클래스 빈도를 미리 알 수 없다), warm_start 에서 데이터로 균형 가중치
        #   dict 를 계산해 직접 넣는다. 초기값은 None(가중치 없음).
        self.clf = SGDClassifier(
            loss='log_loss', alpha=1e-4, class_weight=None,
            random_state=0, warm_start=True)

    def _remember(self, X, y):
        """메모리 버퍼에 표본 누적(상한 초과 시 오래된 것부터 버림)."""
        for xi, yi in zip(X, y):
            self._buf_X.append(np.asarray(xi, dtype=float))
            self._buf_y.append(int(yi))
        if len(self._buf_y) > self._buf_cap:
            drop = len(self._buf_y) - self._buf_cap
            self._buf_X = self._buf_X[drop:]
            self._buf_y = self._buf_y[drop:]

    def _partial_fit(self, X, y):
        """스케일러·분류기 partial_fit 1 라운드(온라인 갱신의 공통 경로)."""
        X = np.asarray(X, dtype=float).reshape(len(y), -1)
        y = np.asarray(y, dtype=int)
        # 스케일러를 먼저 온라인 갱신한 뒤 그 스케일로 변환해 분류기를 갱신한다.
        self.scaler.partial_fit(X)
        Xs = self.scaler.transform(X)
        self.clf.partial_fit(Xs, y, classes=np.array([0, 1]))
        self._fitted = True
        self._classes_seen.update(int(v) for v in np.unique(y))

    # ----- 공개 API -----
    def ready(self):
        """지금 예측을 신뢰해도 되는가.

        학습이 됐고(_fitted), 표본이 최소치 이상이며, 성공·실패 두 클래스를 모두
        관측했을 때만 True. 한쪽 클래스뿐이면 로지스틱 경계가 정의되지 않는다.
        """
        return bool(self.available and self._fitted
                    and self.n_samples >= _MIN_SAMPLES_READY
                    and {0, 1}.issubset(self._classes_seen))

    def epsilon(self, n_samples=None):
        """ε-탐험 확률. 표본이 적을수록 크다(초기 0.2 → 300 표본에서 0.05).

        [근거] 항상 argmax 후보만 고르면 '아직 안 가 본 자세'는 데이터가 영원히
        안 쌓여 모델이 그 영역을 잘못 배운 채 굳는다(선택 편향). 초반에 차선
        후보도 일부러 섞어 탐색하고, 데이터가 쌓이면 탐험을 줄여 성능을 취한다.
        """
        n = self.n_samples if n_samples is None else n_samples
        if n >= _EPS_DECAY_N:
            return _EPS_END
        frac = max(0.0, min(1.0, n / float(_EPS_DECAY_N)))
        return _EPS_START + (_EPS_END - _EPS_START) * frac

    def predict_proba(self, feat):
        """특징 dict → 파지 성공 확률(0~1 float). 추론 불가 상태면 None.

        ready() 로 게이트한 뒤 호출하는 것이 원칙이지만, 방어적으로 미학습
        상태에서는 None 을 돌려 호출측이 폴백하게 한다.
        """
        if not (self.available and self._fitted):
            return None
        x = feat_to_vector(feat).reshape(1, -1)
        try:
            xs = self.scaler.transform(x)
            p = self.clf.predict_proba(xs)[0]
            # clf.classes_ 에서 '1'(성공)의 열을 찾는다(클래스 순서 방어).
            classes = list(self.clf.classes_)
            if 1 in classes:
                return float(p[classes.index(1)])
            return float(p[-1])
        except Exception:                      # noqa: BLE001
            return None

    def update(self, feat, ok):
        """표본 1개 온라인 반영: 버퍼 append + partial_fit 1 스텝.

        메인 노드가 매 파지 시도 종결 직후 (특징, 성공여부)로 호출한다. jsonl
        영속 로깅은 메인 노드가 별도로 하므로 여기서는 파일 I/O 를 하지 않는다
        (ROS 무의존·부작용 최소 원칙).
        """
        if not self.available:
            return
        x = feat_to_vector(feat).reshape(1, -1)
        y = [1 if ok else 0]
        self._partial_fit(x, y)
        self._remember(x, y)
        self.n_samples += 1

    def warm_start(self, jsonl_path, epochs=300):
        """attempts.jsonl 전체로 배치 warm start(여러 에폭 반복 학습).

        노드 시작 시, 그리고 주기적 전체 재적합에서 호출한다. 모델을 새로 만들고
        (편향 누적 방지) 전체 데이터에 스케일러를 맞춘 뒤, 셔플하며 epochs 회
        partial_fit 을 반복해 로지스틱 경계를 수렴시킨다.

        [수천 회 반복 허용] 사용자가 명시적으로 수백~수천 iter 를 승인했다. 이는
        '로봇을 수천 번 돌린다'가 아니라 '이미 모인 데이터를 수천 번 곱씹어
        학습'하는 것이다(오프라인 계산일 뿐이라 안전하다).

        반환: (표본 수, ready 여부).
        """
        if not self.available:
            return (0, False)
        X, y = self._load_jsonl(jsonl_path)
        # 모델을 새로 만들어 과거 상태를 버리고 전체 데이터로 다시 학습한다.
        self._new_model()
        self._fitted = False
        self._classes_seen = set()
        self.n_samples = len(y)
        self._buf_X, self._buf_y = [], []
        if len(y) == 0:
            return (0, False)
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=int)
        self._remember(X, y)
        # 성공/실패 빈도 불균형을 균형 가중치 dict 로 보정해 분류기에 심는다
        # ('balanced' 문자열은 partial_fit 불가라 직접 계산). 한쪽 클래스뿐이면
        # compute_class_weight 가 그 클래스만 1.0 으로 준다.
        present = np.unique(y)
        try:
            w = compute_class_weight('balanced', classes=present, y=y)
            self.clf.class_weight = {int(c): float(wi)
                                     for c, wi in zip(present, w)}
        except Exception:                      # noqa: BLE001
            self.clf.class_weight = None
        # 스케일러는 전체 배치로 한 번에 적합(이후 온라인 partial_fit 이 이어감).
        self.scaler.fit(X)
        Xs = self.scaler.transform(X)
        rng = np.random.default_rng(0)
        classes = np.array([0, 1])
        for _ in range(max(1, int(epochs))):
            idx = rng.permutation(len(y))
            self.clf.partial_fit(Xs[idx], y[idx], classes=classes)
        self._fitted = True
        self._classes_seen.update(int(v) for v in np.unique(y))
        return (self.n_samples, self.ready())

    def explain(self, feat, top_k=3):
        """이 후보를 왜 그 점수로 봤는지 — 표준화 기여도 상위 top_k 문자열.

        기여도 = 로지스틱 가중치(coef) × 표준화된 특징값. 부호가 +면 성공 쪽으로,
        −면 실패 쪽으로 민 특징이다. 선택 이유 로그에 사람이 읽게 쓴다.
        """
        if not (self.available and self._fitted):
            return '(선택기 미학습)'
        x = feat_to_vector(feat).reshape(1, -1)
        try:
            xs = self.scaler.transform(x)[0]
            coef = np.asarray(self.clf.coef_[0], dtype=float)
            contrib = coef * xs
            order = np.argsort(-np.abs(contrib))[:top_k]
            parts = []
            for i in order:
                sign = '+' if contrib[i] >= 0 else '-'
                parts.append(f'{FEATURES[i]}({sign}{abs(contrib[i]):.2f})')
            return ', '.join(parts)
        except Exception:                      # noqa: BLE001
            return '(기여도 계산 실패)'

    def save(self, path):
        """모델·스케일러·상태를 pickle 로 저장. 실패해도 예외를 삼킨다(데모 우선)."""
        if not self.available:
            return False
        try:
            os.makedirs(os.path.dirname(os.path.expanduser(path)), exist_ok=True)
            blob = {
                'features': FEATURES,
                'scaler': self.scaler,
                'clf': self.clf,
                'fitted': self._fitted,
                'n_samples': self.n_samples,
                'classes_seen': sorted(self._classes_seen),
            }
            with open(os.path.expanduser(path), 'wb') as f:
                pickle.dump(blob, f)
            return True
        except Exception:                      # noqa: BLE001
            return False

    def load(self, path):
        """저장된 모델을 복원. 성공 True / 실패(없음·손상·버전불일치) False."""
        if not self.available:
            return False
        try:
            with open(os.path.expanduser(path), 'rb') as f:
                blob = pickle.load(f)
            # 특징 순서가 바뀐 구모델은 열이 어긋나므로 거부(새로 학습하게 둔다).
            if blob.get('features') != FEATURES:
                return False
            self.scaler = blob['scaler']
            self.clf = blob['clf']
            self._fitted = bool(blob.get('fitted', True))
            self.n_samples = int(blob.get('n_samples', 0))
            self._classes_seen = set(blob.get('classes_seen', []))
            return True
        except Exception:                      # noqa: BLE001
            return False

    # ----- jsonl 로더 -----
    @staticmethod
    def _load_jsonl(jsonl_path):
        """attempts.jsonl → (X 리스트, y 리스트). 각 줄은 {"feat":{...},"ok":0|1}.

        깨진 줄이나 feat/ok 누락 줄은 건너뛴다(로그 손상이 학습을 막지 않게).
        """
        X, y = [], []
        p = os.path.expanduser(jsonl_path)
        if not os.path.exists(p):
            return X, y
        with open(p, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    feat = rec['feat']
                    ok = int(rec['ok'])
                except (ValueError, KeyError, TypeError):
                    continue
                # feat 이 dict 가 아닌 줄(개구 실패 등 특징 없는 감사 로그)은
                # 학습에 쓸 수 없으므로 건너뛴다.
                if not isinstance(feat, dict):
                    continue
                X.append(feat_to_vector(feat))
                y.append(1 if ok else 0)
        return X, y
