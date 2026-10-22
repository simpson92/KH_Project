# Issue Log

| 날짜 | 문제 | 원인 | 해결 |
|---|---|---|---|
| 10/12 | prj07 가상환경 activate 실패 | `.venv` 손상 (activate 없음) | `prj07/.venv` 새로 생성 |
| 10/12 | .gitignore 일부 규칙 미동작 | `echo` 명령이 파일에 그대로 기록됨 | 규칙 수정 + prj08 차단 구역 추가 |
| 10/12 | 터미널 `code` 명령 실패 (ENOENT .sock) | 복원된 옛 터미널의 연결 정보 | Developer: Reload Window |
| 10/12 | Ultralytics config not writable 경고 | `~/.config` 폴더 없음 | `mkdir -p ~/.config` |
| 10/12 | Audit: 교과 7 문서 Class 수(4,602)와 FINAL 라벨(4,601) 불일치 | 10/07 QA 이후 10/08 라벨 추가 수정(Class 2→0 56개 등)이 교과 7 문서에 반영 안 됨. 이승훈 10/08 zip = master = subject7_final (diff 0) | 데이터 수정 없음 · 현재 FINAL(4,601)을 kimchi_v1 후보로 팀 확정 필요 · 근거 reports/audit_check.csv |
| 10/12 | 팀원 데이터 버전 불일치 해결 | 10/07본(4,602)과 10/08 수정본(4,601) 혼재 | kimchi_v1 = 10/08 수정본(4,601) 확정 · 5명 라벨 sha256 지문 일치 확인 |
| 10/12 | Leakage 60초 이내 validation 기대 136 / 실제 135 | 1장이 가장 가까운 train과 60.28초 차이 · 교과 7은 초 단위로 잘라 계산(포함) · 교과 8 코드는 마이크로초까지 계산(제외) | 기준 정밀도 차이 · 결론(Leakage 높음)에는 영향 없음 · 기대값 유지 |
| 10/13 | `git pull` 거부 (`divergent branches`) | 내 브랜치와 main 양쪽에 새 커밋 · pull 방식 미설정 | `git config --global pull.rebase false` 후 다시 pull (merge) · 순서: commit → `git pull origin main` → push |
| 10/13 | 다운로드한 스크립트 `cp` 실패 (No such file) | 같은 이름이 있어 브라우저가 `(1)`을 붙여 저장 | `ls`로 실제 파일명 확인 후 복사 · 옛 파일 정리 |
| 10/13 | `manifests/`와 split CSV 내용은 같은데 바이트 비교 불일치 | `csv.DictWriter` 기본 줄바꿈이 `\r\n`(CRLF) | 모든 CSV 쓰기에 `lineterminator="\n"` · 재실행 후 바이트 동일 확인 |
| 10/13 | `manifests/`가 3칸(file_name · capture_group · role) · 값 `bridge` → 가이드 16.1 최소 컬럼 · `bridge_holdout`과 다름 | 06이 split CSV 칸을 그대로 옮김 | `src/manifest.py` + `upgrade_manifest_schema_v1_to_v2`로 v2 9칸 · 배정 변경 0 · 불변 조건 검사 PASS (`manifest_schema_check.csv`) · 다른 검사 결과 변화 없음 · PR #87 |
| 10/13 | 라벨 Preview 때 교과 7 도구로 `data/yolo`를 바로 열면 그 안에 `manifests/`가 생길 위험 | 교과 7 도구는 연 폴더 아래 `manifests/`를 만듦 | 레포 밖 `~/preview_ws/raw/yolo`에 하드 링크(`cp -al`) 작업 공간 · 저장 · QA 버튼 안 누름 · 확인 후 삭제 · 20/20 일치 (`label_preview.md`) |
| 10/13 | Smoke Test 경고 · 이상 결과 6건 (mAP≈0 · Prediction 박스 과다 · `optimizer=auto` · 8.4.176 안내 등) | 1 epoch · 기본 설정 | 모두 정상이거나 4일차에 조치 (optimizer · lr0 고정 · 버전 유지) · 상세 `reports/smoke_test.md` 4장 |
| 10/14 | Val `250411_140005265446` plastic 정답 박스 2개(4K 13×17 · 12×13px · 트레이 위쪽 가장자리 y0.09~0.12)에 실제 이물 없음 | 교과 7 라벨링 때 클릭 실수로 생긴 빈 박스로 추정 | kimchi_v1 유지(Baseline 비교 기준 보존) · 수정은 팀 결정 후 kimchi_v2 · 영향 Val GT 389개 중 2개(0.5%) · 같은 사진 1개(4K 17×13px)는 실제 작은 흰 조각 → 정상 |
| 10/14 | 학습 전 `python: command not found` | venv를 켜지 않고 실행 (WSL에는 `python3`만 있음) | `source .venv/bin/activate` 후 실행 · `python-is-python3` 설치는 하지 않음 (venv 밖에서 실수로 돌아가는 것을 막기 위해) |
| 10/14 | 실행 직후 `KeyboardInterrupt` | 첫 `import torch`가 1~2분 걸려 멈춘 줄 알고 Ctrl+C | 다시 실행하고 기다림 · 두 번째부터는 빠름 |
| 10/14 | `git status`에 `ahead of 'origin/ch' by 76 commits` | `git pull origin main`으로 받은 main 커밋이 아직 내 원격 브랜치(origin/ch)에 없음 | 정상 · `git push origin ch` 하면 사라짐 (local main은 따로 업데이트하지 않아도 됨) |
| 10/14 | Confusion Matrix background 칸 숫자가 수천 개 | Ultralytics가 conf 0.001 이상 예측을 모두 세서 그림 | 그림은 Class 혼동 방향만 참고 · FP 개수는 conf 0.25 기준 `baseline_val_image_check.csv` · `baseline_class_check.csv`로 확인 |
| 10/14 | Val branch 오검출 확인 중 정답 없는 자리에 이물이 보이는 곳 2곳 (`250411_092158458691` 4K (465,888)-(721,983) · `250411_094548003041` 4K (1599,1628)-(1738,1852)) | 교과 7 라벨링 때 작은 이물을 놓친 것으로 추정 (라벨 누락 후보: `…8691` 병해·갈변 Class 5 · `…3041` 돌 Class 1) · 진짜 나뭇가지 라벨 누락은 0건 | kimchi_v1 유지 · 위 라벨 오류 2건과 함께 kimchi_v2 여부 팀 결정 · 근거 `reports/branch_pred_check.csv` no 4 · 5 · 10 (no 4 · 10은 같은 자리 중복 박스 · 메모 갈변/돌 엇갈림 → 10/14 재확인 결과 갈변) |
| 10/14 | 학습 가중치 `baseline_best.pt`를 팀 Discord에 첨부해 공유 | 6일차 branch 확인을 팀원 PC에서 하려고 전달 · README 17장 · 가이드 22.2(학습 Weight 외부 반출 금지) 확인 누락 | Discord 첨부 삭제 · 받은 파일은 각자 PC `models/baseline/`에만 보관 (Git 제외) · 이후 가중치 이동은 기관이 허락한 방법으로만 · 회사 이미지 · 라벨은 공유되지 않음 |
| 10/15 | 6일차 회의 결정 · 라벨 오류 2 · 누락 후보 2 처리 | 고치면 Dataset Version 변경 → Baseline 재평가 필요 · 7일차 해상도 효과와 섞임 · 영향 약 1% | **kimchi_v1 유지** · 기록만 · 수정은 교과 14 인계 목록으로 · 반복 문제 H1 확정 · 7일차 변수 imgsz (smoke 11GB 미만 → 1280 · 이상/OOM → 960) · `reports/failure_hypothesis.md` 8장 |
