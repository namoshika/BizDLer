# BizDLer
Biz∫へログインし、ページから給料明細をダウンロード(html, PDFの2種)するスクリプトです。  

Python3.5製です。  
動作確認は以下のOSで行っております。
* Windows10

# ライセンス
このアプリはMIT Licenseの下にあります。  
Copyright (C) 2016 namoshika

# 使用法
```sh
$ pipenv install
$ pipenv run python ./app.py
# 実行後、./downloadsディレクトリに給料明細が保存されます。
# DL済みの最新月は./config/saveinfo.jsonに保存され、次回実行時には
# 新たにDL可能になったもののみをDLします。
```