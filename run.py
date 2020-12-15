import os
import sys
from datetime import datetime

import pandas as pd
from pandas import DataFrame
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from trello import TrelloClient

NUM_TOPICS = "//*[@id='site-content']/div[2]/div/div[2]/div/div[1]/div/div[1]/div/div[1]"
TOPICS = "//*[@id='site-content']/div[2]/div/div[2]/div/div[2]/a"
TITLE = "div/div[3]/div[1]/p"
CREATED_DATE = "div/div[3]/div[2]/p/span"
LAST_COMMENT = "div/div[4]/div[1]/p/p/a/span[2]"
NUM_COMMENTS = "div/div[4]/div[2]/p"


def get_current_df() -> DataFrame:

    options = Options()
    options.add_argument("--headless")
    executable_path = "/usr/local/bin/chromedriver"
    driver = webdriver.Chrome(chrome_options=options, executable_path=executable_path)
    driver.implicitly_wait(10)
    driver.get("https://www.kaggle.com/c/cassava-leaf-disease-classification/discussion")

    WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.XPATH, NUM_TOPICS)))

    num_topics = driver.find_element_by_xpath(NUM_TOPICS)
    num_topics = int(num_topics.text.split(" ")[0])

    cnt = 0
    while True:

        cnt += 1
        topics = driver.find_elements_by_xpath(TOPICS)
        ActionChains(driver).move_to_element(topics[-1]).perform()

        if len(topics) == num_topics:
            break
        if cnt > 100:
            sys.exit()

    di = {"url": [], "title": [], "created_date": [], "last_comment": [], "num_comments": []}
    for t in topics:

        di["url"].append(t.get_attribute("href"))
        di["title"].append(t.find_element_by_xpath(TITLE).text)
        di["created_date"].append(t.find_element_by_xpath(CREATED_DATE).get_attribute("title"))
        di["last_comment"].append(t.find_element_by_xpath(LAST_COMMENT).get_attribute("title"))
        di["num_comments"].append(t.find_element_by_xpath(NUM_COMMENTS).text)

    driver.quit()
    df = pd.DataFrame.from_dict(di)
    df["created_date"] = df["created_date"].apply(
        lambda x: x.replace(" GMT+0900 (Japan Standard Time)", "")
    )
    df["created_date"] = df["created_date"].apply(
        lambda x: str(datetime.strptime(x, "%a %b %d %Y %H:%M:%S"))
    )

    df["last_comment"] = df["last_comment"].apply(
        lambda x: x.replace(" GMT+0900 (Japan Standard Time)", "")
    )
    df["last_comment"] = df["last_comment"].apply(
        lambda x: str(datetime.strptime(x, "%a %b %d %Y %H:%M:%S"))
    )

    return df


curr_df = get_current_df()
prev_df = pd.read_csv("~/actions-runner/csv/discussion.csv")

client = TrelloClient(api_key=os.environ["API_KEY"], api_secret=os.environ["API_SECRET"])
board = client.get_board(os.environ["BOARD_ID"])

# Add new topics
url_list = set(curr_df["url"]) - set(prev_df["url"])
for url in url_list:
    title = curr_df.loc[curr_df["url"] == url, "title"].item()
    board.get_list(os.environ["TOPICS_LIST_ID"]).add_card(name=title, desc=url)

# Change card with updated comments from Done to Comments list
df = pd.merge(curr_df, prev_df, on=["url"])
df["is_updated"] = df["last_comment_x"] != df["last_comment_y"]
for card in board.get_list(os.environ["DONE_LIST_ID"]).list_cards():
    if card.desc in df.loc[df["is_updated"], "url"].tolist():
        card.change_list(os.environ["COMMENTS_LIST_ID"])

curr_df.to_csv("~/actions-runner/csv/discussion.csv", index=False)
