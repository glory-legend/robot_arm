#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""오프라인 심층 최적화 스크립트 (R6) — ROS 무의존.

attempts.jsonl(파지 시도 로그)을 읽어 GraspSelector 와 '동일한 특징'으로 학습
데이터를 만든 뒤, 수천 회 반복이 허용된 심층 하이퍼파라미터 탐색으로 최적
분류기를 찾는다. 최종 배포 모델은 온라인 갱신(partial_fit) 호환을 위해 SGD
계열을 유지하되, 표본이 충분하면 GradientBoosting 대안까지 교차검증으로 비교해
'무엇이 더 나은지'를 리포트한다.

[왜 GBT 가 이겨도 SGD 를 저장하나]
  런타임 선택기는 매 시도마다 partial_fit 으로 온라인 학습한다. GBT 는 partial_fit
  이 없어 그 파이프라인과 호환되지 않는다. 그래서 GBT 가 교차검증에서 이기면 그
  사실만 리포트하고, 실제 배포 파일에는 최적 하이퍼파라미터로 재학습한 SGD 를
  grasp_selector 가 로드할 수 있는 형식(pickle blob)으로 저장한다.

사용법:
  python3 train_selector.py [--jsonl 경로] [--out 경로]
    --jsonl : 학습 로그 (기본 ~/pick_place_logs/attempts.jsonl)
    --out   : 저장할 모델 (기본 ~/pick_place_logs/selector_model.pkl)
"""

import argparse
import os
import pickle
import sys

import numpy as np

# grasp_selector 와 특징 정의를 공유해 학습/추론이 절대 어긋나지 않게 한다.
from bin_picking.grasp_selector import FEATURES, feat_to_vector, GraspSelector

try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import SGDClassifier
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    _SKLEARN_OK = True
except Exception as exc:                       # noqa: BLE001
    _SKLEARN_OK = False
    _IMPORT_ERR = repr(exc)


def load_dataset(jsonl_path):
    """attempts.jsonl → (X ndarray, y ndarray). GraspSelector 로더를 재사용."""
    X, y = GraspSelector._load_jsonl(jsonl_path)
    if not X:
        return np.empty((0, len(FEATURES))), np.empty((0,), dtype=int)
    return np.asarray(X, dtype=float), np.asarray(y, dtype=int)


def deep_search_sgd(X, y, cv):
    """SGDClassifier(log_loss) 심층 하이퍼파라미터 탐색.

    alpha(정규화), class_weight(불균형), max_iter(에폭)를 그리드로 훑는다.
    ROC-AUC 로 채점(성공/실패 순위 품질 = 우리가 원하는 랭킹 성능).
    반환: (best_pipeline, best_params, best_auc).
    """
    pipe = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', SGDClassifier(loss='log_loss', random_state=0)),
    ])
    # 수천 회 반복 허용 — 데이터에 대한 학습 반복(에폭/탐색)일 뿐이라 안전하다.
    grid = {
        'clf__alpha': [1e-5, 1e-4, 1e-3, 1e-2],
        'clf__class_weight': [None, 'balanced'],
        'clf__max_iter': [500, 1000, 2000, 5000],
        'clf__tol': [1e-4],
    }
    gs = GridSearchCV(pipe, grid, scoring='roc_auc', cv=cv, n_jobs=-1,
                      error_score=0.0)
    gs.fit(X, y)
    return gs.best_estimator_, gs.best_params_, gs.best_score_


def compare_gbt(X, y, cv):
    """표본 충분(>200) 시 GradientBoosting 대안을 교차검증으로 비교.

    반환: (best_auc 또는 None, best_params 또는 None).
    """
    if len(y) <= 200:
        return None, None
    pipe = Pipeline([('clf', GradientBoostingClassifier(random_state=0))])
    grid = {
        'clf__n_estimators': [100, 200],
        'clf__max_depth': [2, 3],
        'clf__learning_rate': [0.05, 0.1],
    }
    gs = GridSearchCV(pipe, grid, scoring='roc_auc', cv=cv, n_jobs=-1,
                      error_score=0.0)
    gs.fit(X, y)
    return gs.best_score_, gs.best_params_


def save_blob(pipeline, n_samples, classes_seen, out_path):
    """최적 SGD 파이프라인을 grasp_selector.load 호환 pickle blob 으로 저장.

    GraspSelector 는 scaler 와 clf 를 따로 읽으므로 파이프라인에서 분리해 담는다.
    저장된 clf 는 여전히 SGDClassifier 라 이후 런타임에서 partial_fit 온라인 갱신을
    이어갈 수 있다.
    """
    scaler = pipeline.named_steps['scaler']
    clf = pipeline.named_steps['clf']
    blob = {
        'features': FEATURES,
        'scaler': scaler,
        'clf': clf,
        'fitted': True,
        'n_samples': int(n_samples),
        'classes_seen': sorted(int(c) for c in classes_seen),
    }
    os.makedirs(os.path.dirname(os.path.expanduser(out_path)), exist_ok=True)
    with open(os.path.expanduser(out_path), 'wb') as f:
        pickle.dump(blob, f)


def main(argv=None):
    ap = argparse.ArgumentParser(description='파지 선택기 오프라인 심층 최적화')
    ap.add_argument('--jsonl', default='~/pick_place_logs/attempts.jsonl',
                    help='학습 로그 경로')
    ap.add_argument('--out', default='~/pick_place_logs/selector_model.pkl',
                    help='저장할 모델 경로')
    args = ap.parse_args(argv)

    if not _SKLEARN_OK:
        print(f'[오류] sklearn 임포트 실패: {_IMPORT_ERR}')
        return 1

    X, y = load_dataset(args.jsonl)
    n = len(y)
    print(f'== 데이터 로드: {n} 표본 (경로 {os.path.expanduser(args.jsonl)}) ==')
    if n == 0:
        print('[중단] 학습 표본이 없습니다. 먼저 데모를 돌려 attempts.jsonl 을 쌓으세요.')
        return 1
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    print(f'  성공(1) {n_pos}개 / 실패(0) {n_neg}개')
    if n_pos == 0 or n_neg == 0:
        print('[중단] 한쪽 클래스뿐이라 분류기를 학습할 수 없습니다(양쪽 라벨 필요).')
        return 1

    # 교차검증 fold 수 — 소수 클래스 표본 수를 넘지 않게(각 fold 에 양쪽 존재 보장).
    n_splits = max(2, min(5, n_pos, n_neg))
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=0)
    print(f'== {n_splits}-fold StratifiedKFold 교차검증으로 심층 탐색 시작 ==')

    best_pipe, best_params, best_auc = deep_search_sgd(X, y, cv)
    print('\n-- SGDClassifier(log_loss) 최적 --')
    print(f'  최적 하이퍼파라미터: {best_params}')
    print(f'  교차검증 ROC-AUC   : {best_auc:.4f}')

    # GBT 대안 비교(표본 충분 시).
    gbt_auc, gbt_params = compare_gbt(X, y, cv)
    if gbt_auc is not None:
        print('\n-- GradientBoosting 대안(참고용) --')
        print(f'  최적 하이퍼파라미터: {gbt_params}')
        print(f'  교차검증 ROC-AUC   : {gbt_auc:.4f}')
        if gbt_auc > best_auc + 1e-6:
            print('  → GBT 가 더 우수하나, 온라인 partial_fit 호환을 위해 배포는 '
                  'SGD 를 유지합니다(리포트만).')
        else:
            print('  → SGD 가 동등하거나 우수합니다.')
    else:
        print('\n-- GradientBoosting 대안: 표본 <200 로 생략 --')

    # 전체 데이터로 최적 SGD 재학습(GridSearch 는 이미 best_estimator_ 를 전체
    # 데이터에 refit 하지만, 명시적으로 fit 해 두어 저장 상태를 확정한다).
    best_pipe.fit(X, y)
    y_prob = best_pipe.predict_proba(X)[:, list(best_pipe.named_steps['clf'].classes_).index(1)]
    y_pred = best_pipe.predict(X)
    print('\n== 전체 데이터 성능(학습셋 기준, 참고) ==')
    print(f'  정확도   : {accuracy_score(y, y_pred):.4f}')
    print(f'  ROC-AUC  : {roc_auc_score(y, y_prob):.4f}')

    # 특징 가중치(표준화 공간) 리포트 — 크기순.
    coef = np.asarray(best_pipe.named_steps['clf'].coef_[0], dtype=float)
    order = np.argsort(-np.abs(coef))
    print('\n== 특징 가중치(표준화 계수, |크기| 내림차순) ==')
    for i in order:
        print(f'  {FEATURES[i]:>10s}: {coef[i]:+.4f}')

    save_blob(best_pipe, n, np.unique(y), args.out)
    print(f'\n== 저장 완료 → {os.path.expanduser(args.out)} '
          f'(grasp_selector.load 호환) ==')
    return 0


if __name__ == '__main__':
    sys.exit(main())
