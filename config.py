import json
import os

class Config:
    def __init__(self, dirPath: str):
        self.file_auth = os.path.join(dirPath, "config", "authinfo.json")
        self.file_date = os.path.join(dirPath, "config","saveinfo.json")
        with open(self.file_auth, "r", encoding="utf8") as authfile:
            self.AuthInfos = json.load(authfile)
        try:
            with open(self.file_date, "r", encoding="utf8") as saveFile:
                saveInfos = json.load(saveFile)
            self.CurrentYear = int(saveInfos["year_selector_opt"])
            self.CurrentMonth = int(saveInfos["month_selector_opt"])
        except FileNotFoundError as e:
            self.CurrentYear = -1
            self.CurrentMonth = -1
    def save(self):
        with open(self.file_date, "w", encoding="utf8") as saveFile:
            saveInfos = {
                "year_selector_opt": self.CurrentYear,
                "month_selector_opt": self.CurrentMonth
            }
            json.dump(saveInfos, saveFile)
