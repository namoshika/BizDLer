import http.cookiejar
import json
import logging
import os
import sys
import urllib.request
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common import exceptions as drivererrors

logging.basicConfig(level=logging.ERROR)

# 設定値
AUTH_FILE = os.path.join(".", "config", "authinfo.json")
LATEST_DATE_FILE = os.path.join(".", "config", "saveinfo.json")
DOWNLOAD_DIR = os.path.join(".", "downloads")
PHANTOMJS_DIR = os.path.join(".", "lib", "phantomjs")
# 初期化
cookies = http.cookiejar.CookieJar()
httpClient = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
httpClient.addheaders = [
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"),
    ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"),
    ("Accept-Language", "ja,en-US;q=0.8,en;q=0.6")
]
# 設定ファイル読込み、DL先作成
currentYear = None
currentMonth = None
try:
    logging.info("phase1: launch phantomJS")
    driver = \
        webdriver.Chrome(r".\lib\chromedriver.exe") if "--debug" in sys.argv else \
        webdriver.PhantomJS(PHANTOMJS_DIR)
    
    logging.info("phase2: load config")
    if os.path.isdir(DOWNLOAD_DIR) == False:
        os.mkdir(DOWNLOAD_DIR)
    with open(AUTH_FILE, "r", encoding="utf8") as authfile:
        authInfos = json.load(authfile)
        logging.info(authInfos)
    with open(LATEST_DATE_FILE, "r", encoding="utf8") as saveFile:
        saveInfos = json.load(saveFile)
        logging.info(saveInfos)
        currentYear = int(saveInfos["year_selector_opt"])
        currentMonth = int(saveInfos["month_selector_opt"])
except FileNotFoundError as e:
    if e.filename == LATEST_DATE_FILE:
        logging.warning("Not found \"{0}\". It's maked.".format(LATEST_DATE_FILE))
        currentYear = -1
        currentMonth = -1
        saveInfos = {
            "year_selector_opt": currentYear,
            "month_selector_opt": currentMonth
        }
    else:
        logging.exception(e)
        raise
except drivererrors.WebDriverException as e:
    logging.exception(e)
    raise
except IOError as e:
    logging.exception(e)
    raise

# DL処理本体
try:    
    logging.info("phase3: auth seq 1")
    driver.get(authInfos["authA"]["targetUrl"])
    driver.find_element_by_name("username").send_keys(authInfos["authA"]["username"])
    driver.find_element_by_name("password").send_keys(authInfos["authA"]["password"])
    driver.find_element_by_id("btnSubmit_6").click()
    currentUrl = urllib.parse.urlparse(driver.current_url)
    if "p=user-confirm" in currentUrl.query:
        driver.find_element_by_id("btnContinue").click()

    logging.info("phase4: auth seq 2")
    driver.get(authInfos["authB"]["targetUrl"])
    driver.find_element_by_name("USR_ID").send_keys(authInfos["authB"]["username"])
    driver.find_element_by_name("PASSWD").send_keys(authInfos["authB"]["password"])
    driver.find_element_by_name("a_login").click()

    # メニューを開く。初回以外でクリックを
    # するとメニューを閉じてしまうため、初回のみ押す。
    logging.info("phase5: navigate menu")
    driver.switch_to_frame(driver.find_element_by_name("PC00MENU"))
    driver.find_element_by_id("80").click()

    logging.info("phase6: dl files")
    while True:
        logging.info("parsing html")
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
        #次月が無ければ次年度の月初。次年度が無ければループ終了
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
        else: break
        
        # 通信パラメータ生成
        driver.switch_to_frame(driver.find_element_by_name("PC00CONTENTS"))
        doc = BeautifulSoup(driver.page_source, "html5lib")
        form = doc.find("form")
        targetUrl = urllib.parse.urljoin(driver.current_url, form.get("action"))
        opts = form("input")
        opts = dict(map(lambda itm: (itm.get("name"), itm.get("value")), opts))
        opts.update(authInfos["dl_paystat"]["data"])
        for itmKey, itmVal in opts.items():
            opts[itmKey] = itmVal if itmVal is not None else ""
        if "BT_PRINT" in opts:
            opts.pop("BT_PRINT")
        data = urllib.parse.urlencode(opts, encoding="shift-jis")
        for itm in driver.get_cookies():
            cookies.set_cookie(
                http.cookiejar.Cookie(
                    version=0
                    , name=itm['name']
                    , value=itm['value']
                    , port='80'
                    , port_specified=False
                    , domain=itm['domain']
                    , domain_specified=True
                    , domain_initial_dot=False
                    , path=itm['path']
                    , path_specified=True
                    , secure=itm['secure']
                    , expires=None
                    , discard=False
                    , comment=None
                    , comment_url=None
                    , rest=None
                    , rfc2109=False
                )
            )

        # 明細PDF取得 & 保存
        logging.info("downloading PDF")
        filePathBase = os.path.join(DOWNLOAD_DIR, (\
            "{0}{1}_給料明細".format(currentYear, currentMonthTxt[0:2]) if "給与" in currentMonthTxt else \
            "{0}{1}_賞与明細".format(currentYear, "04" if currentMonthTxt[0:2] == "下期" else "10") if "賞与" in currentMonthTxt else \
            "{0}00_{1}".format(currentYear, currentMonthTxt)))
        logging.info("filePathBase: {0}".format(filePathBase))
        with httpClient.open(targetUrl, data.encode("shift-jis")) as res:
            resDt = res.read()
            with open(filePathBase + ".pdf", "wb") as pdfFile:
                pdfFile.write(resDt)
            pass
        # 明細HTML取得 & 保存
        logging.info("downloading HTML")
        driver.switch_to_frame(None)
        driver.switch_to_frame(driver.find_element_by_name("PC00DETAILS"))
        docTxt = driver.page_source
        with open(filePathBase + ".html", "wt", encoding="utf8") as htmlFile:
            htmlFile.write(docTxt)

        saveInfos["year_selector_opt"] = currentYear
        saveInfos["month_selector_opt"] = currentMonth

    with open(LATEST_DATE_FILE, "w", encoding="utf8") as saveFile:
        json.dump(saveInfos, saveFile)
except Exception as e:
    logging.exception(e)
    logging.error(driver.page_source)
    raise
finally:
    driver.close()
