import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import googlemaps
import threading
import os

class GeoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Maps Geocoding / Reverse Geocoding")
        self.df = None
        self.results = []
        self.api_key = None
        self.gmaps = None
        self.file_path = None

        # API 키 읽기
        self.load_api_key()

        # UI 요소
        self.load_button = tk.Button(root, text="CSV 파일 열기", command=self.load_csv)
        self.load_button.pack(pady=5)

        self.column_listbox = tk.Listbox(root, selectmode=tk.SINGLE, width=50)
        self.column_listbox.pack(pady=5)

        self.process_button = tk.Button(root, text="지오코딩 처리 시작", command=self.start_processing)
        self.process_button.pack(pady=5)
        self.process_button.config(state=tk.DISABLED)

        self.output_text = tk.Text(root, height=20, width=80)
        self.output_text.pack(pady=10)

    def load_api_key(self):
        try:
            with open("api_key.txt", "r", encoding="utf-8") as f:
                key = f.readline().strip()
                if not key:
                    raise ValueError("API 키가 비어있습니다.")
                self.api_key = key
                self.gmaps = googlemaps.Client(key=self.api_key)
        except Exception as e:
            messagebox.showerror("API 키 오류", f"api_key.txt 파일을 읽는 중 오류 발생:\n{e}")
            self.root.destroy()

    def load_csv(self):
        path = filedialog.askopenfilename(title="CSV 파일 선택", filetypes=[("CSV 파일", "*.csv")])
        if not path:
            return
        try:
            self.df = pd.read_csv(path)
            self.file_path = path
            self.column_listbox.delete(0, tk.END)
            for col in self.df.columns:
                self.column_listbox.insert(tk.END, col)
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, f"'{os.path.basename(path)}' 파일을 성공적으로 불러왔습니다.\n컬럼을 선택하세요.\n")
            self.process_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("CSV 오류", f"CSV 파일을 여는 중 오류 발생:\n{e}")

    def start_processing(self):
        if self.df is None or self.df.empty:
            messagebox.showwarning("경고", "CSV 파일을 먼저 불러오세요.")
            return
        sel = self.column_listbox.curselection()
        if not sel:
            messagebox.showwarning("경고", "컬럼을 선택하세요.")
            return
        self.process_button.config(state=tk.DISABLED)
        self.output_text.delete(1.0, tk.END)
        self.results = []

        thread = threading.Thread(target=self.process_column, args=(self.column_listbox.get(sel[0]),))
        thread.start()

    def process_column(self, col_name):
        total = len(self.df[col_name].dropna())
        self.append_output(f"총 {total}개 데이터에 대해 처리 시작...\n")

        for idx, val in self.df[col_name].dropna().items():
            current = idx + 1 if idx + 1 <= total else total
            #self.append_output(f"[{current}/{total}] 처리 중: {val}")

            try:
                if self.is_latlon(val):
                    # 역지오코딩
                    lat, lon = map(float, val.split(","))
                    res = self.gmaps.reverse_geocode((lat, lon))
                    address = res[0]["formatted_address"] if res else "주소 없음"
                    self.results.append({"원본값": val, "결과": address})
                    self.append_output(f"[{current}/{total}] {val}의 주소: {address}")
                else:
                    # 지오코딩
                    res = self.gmaps.geocode(val)
                    if res:
                        loc = res[0]["geometry"]["location"]
                        coord_lat = f"{loc['lat']}"
                        coord_lng = f"{loc['lng']}"
                        self.results.append({"원본값": val, "위도": coord_lat, "경도": coord_lng})
                        self.append_output(f"[{current}/{total}] {val}의 위도 {coord_lat}, 경도{coord_lng}")
                    else:
                        self.results.append({"원본값": val, "위도": "", "경도": ""})
                        self.append_output(f"[{current}/{total}] {val}의 좌표 없음")
            except Exception as e:
                self.results.append({"원본값": val, "결과": f"오류: {e}"})
                self.append_output(f"오류 발생: {e}")

        self.append_output("\n처리가 완료되었습니다!")
        self.save_results()

        self.process_button.config(state=tk.NORMAL)

    def append_output(self, text):
        def inner():
            self.output_text.insert(tk.END, text + "\n")
            self.output_text.see(tk.END)
        self.root.after(0, inner)

    def is_latlon(self, val):
        try:
            if isinstance(val, str) and ',' in val:
                lat_str, lon_str = val.split(",", 1)
                float(lat_str.strip())
                float(lon_str.strip())
                return True
            return False
        except:
            return False

    def save_results(self):
        folder = os.path.dirname(self.file_path)
        filename = os.path.splitext(os.path.basename(self.file_path))[0]

        # 역지오코딩이면 _addresses.csv, 지오코딩이면 _coordinates.csv로 저장
        if not self.results:
            messagebox.showwarning("경고", "저장할 결과가 없습니다.")
            return

        is_reverse = "주소" in self.results[0]
        out_name = f"{filename}_addresses.csv" if is_reverse else f"{filename}_coordinates.csv"
        out_path = os.path.join(folder, out_name)

        try:
            pd.DataFrame(self.results).to_csv(out_path, index=False, encoding="utf-8-sig")
            self.append_output(f"결과가 '{out_name}' 이름으로 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("저장 오류", f"결과 저장 중 오류 발생:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = GeoApp(root)
    root.mainloop()
