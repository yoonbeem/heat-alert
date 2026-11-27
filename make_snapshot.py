r"""PC에서 받은 전국 무더위쉼터 자료를 data/shelters.csv 로 저장하는 도구.

왜 필요한가: 재난안전데이터 API는 등록된(국내) IP에서만 응답해서,
해외에 있는 Streamlit Cloud 서버에서는 'UNREGISTERED IP ERROR'가 나요.
그래서 PC에서 받은 자료를 파일로 만들어 GitHub에 같이 올리고, 클라우드 앱은 그 파일을 읽습니다.

사용법 (heat_alert 폴더에서): .\.venv\Scripts\python.exe make_snapshot.py
자료를 새로 고치고 싶을 때 다시 실행한 뒤 data\shelters.csv 를 GitHub에 다시 올리면 돼요.
"""
import tomllib
from datetime import date
from pathlib import Path

import shelters

here = Path(__file__).parent
key = tomllib.load(open(here / ".streamlit" / "secrets.toml", "rb"))["SHELTER_API_KEY"].strip()
df = shelters.standardize(shelters.fetch_from_api(key))
df["위도"] = df["위도"].round(6)
df["경도"] = df["경도"].round(6)
df = df.astype(object).where(df.notna(), "-")  # 빈칸은 '-'로
shelters.CSV_PATH.parent.mkdir(exist_ok=True)
df.to_csv(shelters.CSV_PATH, index=False, encoding="utf-8-sig")
(shelters.CSV_PATH.parent / "shelters_date.txt").write_text(date.today().isoformat(), encoding="utf-8")
print(f"{len(df)}곳 저장: {shelters.CSV_PATH} ({shelters.CSV_PATH.stat().st_size / 1e6:.1f} MB)")
