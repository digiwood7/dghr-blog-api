"""
Cafe24 FTP Service
FTP 파일 업로드 및 관리
"""
import os
import ftplib
from io import BytesIO
from datetime import datetime
from pathlib import Path


class Cafe24FTP:
    """Cafe24 FTP 클라이언트"""

    def __init__(self):
        self.host = os.getenv("FTP_HOST", "114.207.244.217")
        self.port = int(os.getenv("FTP_PORT", "21"))
        self.user = os.getenv("FTP_USER", "jyk980")
        self.password = os.getenv("FTP_PASS", "")
        self.base_url = os.getenv("FTP_BASE_URL", "http://jyk980.cafe24.com")
        self.ftp = None

    def connect(self):
        """FTP 서버 연결"""
        self.ftp = ftplib.FTP()
        self.ftp.connect(self.host, self.port)
        self.ftp.login(self.user, self.password)

    def ensure_dir(self, remote_dir: str):
        """원격 디렉토리가 없으면 생성"""
        dirs = remote_dir.strip("/").split("/")
        current = ""
        for d in dirs:
            current = f"{current}/{d}"
            try:
                self.ftp.cwd(current)
            except:
                self.ftp.mkd(current)
                self.ftp.cwd(current)
        self.ftp.cwd("/")

    def upload_bytes(self, data: bytes, remote_path: str) -> str:
        """바이트 데이터를 FTP로 업로드, 공개 URL 반환"""
        remote_dir = "/".join(remote_path.rsplit("/", 1)[:-1])
        if remote_dir:
            self.ensure_dir(remote_dir)
        self.ftp.storbinary(f"STOR {remote_path}", BytesIO(data))
        # /www/blog/... -> /blog/... 로 변환하여 공개 URL 생성
        public_path = remote_path.replace("/www/blog/", "/blog/")
        return f"{self.base_url}{public_path}"

    def delete_file(self, remote_path: str) -> bool:
        """FTP 파일 삭제"""
        try:
            self.ftp.delete(remote_path)
            return True
        except:
            return False

    def delete_directory(self, remote_path: str) -> bool:
        """FTP 디렉토리 삭제 (재귀적)"""
        try:
            # 디렉토리 내 파일 목록
            self.ftp.cwd(remote_path)
            items = self.ftp.nlst()

            for item in items:
                if item in ['.', '..']:
                    continue
                try:
                    # 파일 삭제 시도
                    self.ftp.delete(item)
                except:
                    # 실패하면 디렉토리로 간주하고 재귀 삭제
                    self.delete_directory(f"{remote_path}/{item}")

            # 상위로 이동 후 디렉토리 삭제
            self.ftp.cwd("..")
            folder_name = remote_path.rstrip("/").split("/")[-1]
            self.ftp.rmd(folder_name)
            return True
        except Exception as e:
            print(f"FTP directory delete error: {e}")
            return False

    def close(self):
        """FTP 연결 종료"""
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                self.ftp.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()


def generate_ftp_path(project_id: str) -> str:
    """FTP 저장 경로 생성: /www/blog/YYYY_MM_dd_{project_id}/"""
    date_prefix = datetime.now().strftime("%Y_%m_%d")
    return f"/www/blog/{date_prefix}_{project_id}"


def generate_filename(original: str, keyword: str) -> str:
    """파일명 생성: {keyword}_{timestamp}.확장자"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = Path(original).suffix.lower()
    return f"{keyword}_{ts}{ext}"
