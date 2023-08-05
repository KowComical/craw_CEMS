import requests
import os
import pandas as pd
import json
from datetime import date, timedelta
import time
import random
import os.path
import traceback
import numpy as np

import cloudscraper
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

global_path = '.'
file_path = os.path.join(global_path, 'data')
tool_path = os.path.join(global_path, 'tools')


def main():
    start_date = date(2020, 1, 1)
    end_date = date.today()
    try:
        craw_data(start_date, end_date)
    except Exception as e:
        traceback.print_exc()


def find_certain_file(certain_time):
    all_file = search_file(file_path)
    all_file = [all_file[i] for i, x in enumerate(all_file) if x.find(certain_time) != -1]
    if all_file:
        return all_file[0]
    else:
        return None


def search_file(file_path):
    import os

    file_name = []
    for parent, surnames, filenames in os.walk(file_path):
        for fn in filenames:
            file_name.append(os.path.join(parent, fn))
    return file_name


def find_requests(driver, company_selector=None, luzi_selector=None, data_selector=None):
    company_url = None
    luzi_url = None
    data_url = None

    for log_entry in driver.get_log('performance'):
        try:
            log_data = json.loads(log_entry['message'])
            request_url = log_data['message']['params']['request']['url']

            if company_selector and company_selector in request_url:
                company_url = request_url
            elif luzi_selector and luzi_selector in request_url:
                luzi_url = request_url
            elif data_selector and data_selector in request_url:
                data_url = request_url

            if company_url and luzi_url and data_url:
                break

        except (json.JSONDecodeError, KeyError, requests.exceptions.RequestException):
            pass

    return company_url, luzi_url, data_url


def setup_webdriver():
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument('--enable-logging')
    chrome_options.add_argument('--v=1')
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    driver = uc.Chrome(options=chrome_options)
    driver.implicitly_wait(10)

    return driver


def load_website(driver, url):
    driver.get(url)  # 打开要爬的网址


def close_homepage_banner(driver):
    driver.find_element(By.XPATH, '//*[@id="gkClose"]').click()  # 关掉首页黄色通知


def open_dropdown_menu(driver):
    driver.find_element(By.XPATH, '//*[@id="psListShowBtn"]').click()  # 点开下拉菜单


def select_company(driver, company_name):
    driver.find_element(By.XPATH, f"//li[contains(., '{company_name}')]").click()  # 点击公司名


def select_datamonitor(driver):
    driver.find_element(By.XPATH, '//*[@id="monitordata"]').click()


def create_replacement_dict(first_string, provided_dict):
    first_url = urlparse(first_string)
    first_query_params = parse_qs(first_url.query)
    replacement_dict = {}

    for key, value in provided_dict.items():
        if key != 'pscode' and key != 'outputcode' and key != 'day':
            replacement_dict[key] = first_query_params[key][0]
        else:
            replacement_dict[key] = provided_dict[key]

    return replacement_dict


def replace_query_params_with_dict(url_string, replacement_dict):
    # Parse URL and extract query parameters
    url = urlparse(url_string)
    query_params = parse_qs(url.query)

    # Replace query parameters in the URL with values from the dictionary
    for key in replacement_dict:
        query_params[key] = replacement_dict[key]

    # Construct the modified URL
    modified_query = urlencode(query_params, doseq=True)
    modified_url = urlunparse((url.scheme, url.netloc, url.path, url.params, modified_query, url.fragment))

    return modified_url


def craw_cookie():
    url = 'https://ljgk.envsc.cn/'

    company_name = '温州龙湾伟明环保能源有限公司'
    select_company_url = 'GetPSList.ashx'
    select_luzi_url = 'GetBurnList.ashx'
    select_data_url = 'GetMonitorDataList.ashx'

    wd = setup_webdriver()
    load_website(wd, url)
    close_homepage_banner(wd)
    open_dropdown_menu(wd)
    time.sleep(5)
    select_company(wd, company_name)
    select_datamonitor(wd)

    company_url, _, data_url = find_requests(wd, select_company_url, select_luzi_url, select_data_url)

    return wd, company_url, data_url


def craw_data(start_date, end_date=None):
    try:
        delta = timedelta(days=1)

        df_code = pd.read_csv(os.path.join(tool_path, 'luzi_code.csv'))
        ps_code_list = df_code['ps_code'].unique()

        provided_dict = {
            'pscode': 'pscode',
            'outputcode': 'outputcode',
            'day': 'day',
            'SystemType': 'NewSystemType',
            'sgn': 'NewSgnValue',
            'ts': 'NewTsValue',
            'tc': 'NewTcValue'
        }

        wd, company_url, data_url = craw_cookie()
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True})
            # 全公司信息
            company_html = scraper.get(company_url)
            all_company = pd.json_normalize(company_html.json())
            all_company.to_csv(os.path.join(tool_path, 'company_information.csv'), index=False, encoding='utf_8_sig')
        finally:
            wd.close()

        # all_company = pd.read_csv(os.path.join(tool_path, 'company_information.csv'))
        current_date = start_date
        while current_date < end_date:
            current_date_str = current_date.strftime('%Y%m%d')

            current_date_year = current_date.strftime('%Y')
            os.makedirs(current_date_year, exist_ok=True)

            current_date_year_month = current_date.strftime('%Y-%m')

            year_month_path = find_certain_file(current_date_year_month)

            if year_month_path is not None:
                df_year_month = pd.read_csv(year_month_path)
                df_year_month['day'] = df_year_month['day'].astype(str)
            else:  # 如果这个文件不存在则创建新的
                column_names = ['ps_code', 'mp_code', 'monitor_time', 'pollutant_code', 'pollutant_name',
                                'strength', 'standard_value', 'remark', 'status', 'data_status',
                                'create_time', 'update_time', 'day', 'company']

                df_year_month = pd.DataFrame(columns=column_names)

                year_month_path = os.path.join(file_path, current_date_year, f'{current_date_year_month}.csv')
                df_year_month.to_csv(year_month_path, index=False, encoding='utf_8_sig')

            for ps in ps_code_list:
                # 获取公司名称
                company_name = all_company[all_company['ps_code'] == ps]['ps_name'].tolist()[0]
                # 查看这个公司这个日期是否存在
                df_specific = df_year_month[
                    (df_year_month['company'] == company_name) & (df_year_month['day'] == current_date_str)]

                if len(df_specific) == 0:

                    mp_code_list = df_code[df_code['ps_code'] == ps]['mp_code'].unique()
                    df_final = pd.DataFrame()
                    for mp in mp_code_list:
                        provided_dict['pscode'] = ps
                        provided_dict['outputcode'] = mp
                        provided_dict['day'] = current_date_str

                        while True:
                            replacement_dict = create_replacement_dict(data_url, provided_dict)
                            real_data_url = replace_query_params_with_dict(data_url, replacement_dict)
                            # 开始爬取数据
                            time.sleep(random.uniform(5, 10))
                            try:
                                temp_data = scraper.get(real_data_url).json()
                            except requests.exceptions.JSONDecodeError as e:
                                temp_data = None
                            if isinstance(temp_data, list) and temp_data is not None:
                                break
                            else:
                                wd, company_url, data_url = craw_cookie()
                                scraper = cloudscraper.create_scraper(
                                    browser={
                                        'browser': 'chrome',
                                        'platform': 'windows',
                                        'desktop': True})
                                all_company = pd.read_csv(os.path.join(tool_path, 'company_information.csv'))
                                wd.close()
                        df_data = pd.DataFrame()

                        for i in range(len(temp_data)):
                            test = pd.json_normalize(temp_data[i])
                            df_data = pd.concat([df_data, test]).reset_index(drop=True)

                        df_final = pd.concat([df_final, df_data]).reset_index(drop=True)
                    if len(df_final) != 0:
                        df_final['company'] = company_name
                    else:
                        data = {'ps_code': [np.nan],
                                'mp_code': [np.nan],
                                'monitor_time': [np.nan],
                                'pollutant_code': [np.nan],
                                'pollutant_name': [np.nan],
                                'strength': [np.nan],
                                'standard_value': [np.nan],
                                'remark': [np.nan],
                                'status': [np.nan],
                                'data_status': [np.nan],
                                'create_time': [np.nan],
                                'update_time': [np.nan],
                                'day': [current_date_str],
                                'company': [company_name]}

                        df_final = pd.DataFrame(data)

                    df_final.to_csv(year_month_path, index=False, encoding='utf_8_sig', mode='a', header=False)
                    # print(f'{company_name} - {current_date} - Finished')
                    time.sleep(random.uniform(5, 10))
            print(f'{current_date} - Finished')
            current_date += delta
        return
    except Exception as e:
        traceback.print_exc()
        return


if __name__ == '__main__':
    main()
