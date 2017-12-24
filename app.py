#!/usr/bin/python3
import datetime
import logging
import os
import shutil
import sys
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.common import exceptions as drivererrors
from config import Config

# 初期化
BASE_DIR = os.path.dirname(__file__)
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
options = webdriver.ChromeOptions()
options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False
})

# 設定ファイル読込み
logger.info("Load config")
if os.path.isdir(DOWNLOAD_DIR) == False:
    os.mkdir(DOWNLOAD_DIR)
config = Config(BASE_DIR)
currentYear = config.CurrentYear
currentMonth = config.CurrentMonth

# ブラウザ起動
logger.info("Launch Browser")
driver = webdriver.Chrome(".\\lib\\chromedriver.exe", options=options)
# DL処理本体
try:
    logger.info("Auth A")
    driver.get(config.AuthInfos["authA"]["targetUrl"])
    driver.find_element_by_name("username").send_keys(
        config.AuthInfos["authA"]["username"])
    driver.find_element_by_name("password").send_keys(
        config.AuthInfos["authA"]["password"])
    driver.find_element_by_id("btnSubmit_6").click()
    currentUrl = urlparse(driver.current_url)
    if "p=user-confirm" in currentUrl.query:
        driver.find_element_by_id("btnContinue").click()

    logger.info("Auth B")
    driver.get(config.AuthInfos["authB"]["targetUrl"])
    driver.find_element_by_name("USR_ID").send_keys(
        config.AuthInfos["authB"]["username"])
    driver.find_element_by_name("PASSWD").send_keys(
        config.AuthInfos["authB"]["password"])
    driver.find_element_by_name("a_login").click()

    # メニューを開く。初回以外でクリックを
    # するとメニューを閉じてしまうため、初回のみ押す。
    logger.info("Browser: navigate menu")
    driver.switch_to_frame(driver.find_element_by_name("PC00MENU"))
    driver.find_element_by_id("80").click()

    logger.info("Browser: dl files")
    while True:
        logger.info("parsing html")
        # 目的のリンクを押す
        driver.switch_to_default_content()
        driver.switch_to_frame(driver.find_element_by_name("PC00MENU"))
        ele = driver.find_element_by_id("81")
        for itm in ele.find_elements_by_tag_name("a"):
            if itm.text == "明細照会":
                itm.click()
                break

        # 参照年選択
        driver.switch_to_default_content()
        driver.switch_to_frame(driver.find_element_by_name("PC00CONTENTS"))
        ele_year = driver.find_element_by_id("OUT_YEAR")
        selector_year = webdriver.support.select.Select(ele_year)
        currentYear = \
            min([int(optObj.get_attribute("value"))
                 for optObj in selector_year.options
                 if int(optObj.get_attribute("value")) >= currentYear])
        nextYear = \
            min([int(optObj.get_attribute("value"))
                 for optObj in selector_year.options
                 if int(optObj.get_attribute("value")) > currentYear],
                default=None)
        selector_year.select_by_value(str(currentYear))
        # 参照月選択
        driver.switch_to_default_content()
        driver.switch_to_frame(driver.find_element_by_name("PC00CONTENTS"))
        ele = driver.find_element_by_id("OUT_MONTH")
        selector_month = webdriver.support.select.Select(ele)
        nextMonth = \
            min((int(optObj.get_attribute("value"))
                 for optObj in selector_month.options
                 if int(optObj.get_attribute("value")) > currentMonth),
                default=None)
        # 次月が無ければ次年度の月初。次年度が無ければループ終了
        if nextMonth is not None:
            currentMonth = nextMonth
            selector_month.select_by_value(str(nextMonth))
            currentMonthTxt = selector_month.first_selected_option.text
            driver.find_element_by_id("BT_OK").click()
        elif nextYear is not None:
            currentYear = nextYear
            currentMonth = -1
            nextMonth = -1
            continue
        else:
            break

        # 明細PDF取得 & 保存
        logger.info("downloading PDF")
        driver.switch_to_frame(driver.find_element_by_name("PC00CONTENTS"))
        beforeList = set(os.listdir(DOWNLOAD_DIR))
        driver.find_element_by_id("BT_PRINT").click()
        time.sleep(0.5)
        afterList = set(os.listdir(DOWNLOAD_DIR))
        savedFile = os.path.join(DOWNLOAD_DIR, (afterList - beforeList).pop())
        filePathBase = os.path.join(DOWNLOAD_DIR, (
            "{0}{1}_給料明細".format(currentYear, currentMonthTxt[0:2]) if "給与" in currentMonthTxt else
            "{0}{1}_賞与明細".format(currentYear, "04" if currentMonthTxt[0:2] == "下期" else "10") if "賞与" in currentMonthTxt else
            "{0}00_{1}".format(currentYear, currentMonthTxt)))
        logger.info("filePathBase: {0}".format(filePathBase))
        pdfFilePath = filePathBase + ".pdf"
        if os.path.isfile(pdfFilePath):
            os.remove(pdfFilePath)
        shutil.move(savedFile, pdfFilePath)

        # 明細HTML取得 & 保存
        logger.info("downloading HTML")
        driver.switch_to_frame(None)
        driver.switch_to_frame(driver.find_element_by_name("PC00DETAILS"))
        docTxt = driver.page_source
        with open(filePathBase + ".html", "wt", encoding="utf8") as htmlFile:
            htmlFile.write(docTxt)
        config.save()
except Exception as e:
    logging.exception(e)
    logging.error(driver.page_source)
    raise
finally:
    driver.close()
