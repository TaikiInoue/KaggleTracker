import os
import sys
from datetime import datetime

import pandas as pd
from pandas import DataFrame
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from trello import TrelloClient


def get_current_df() -> DataFrame:

    options = Options()
    options.add_argument("--headless")
    executable_path = "/usr/local/bin/chromedriver"
    driver = webdriver.Chrome(chrome_options=options, executable_path=executable_path)
    driver.implicitly_wait(10)
    driver.get("https://www.kaggle.com/c/cassava-leaf-disease-classification/discussion")

    num_topics = driver.find_element_by_xpath("//div[@class='sc-kIpgsX cRxfVQ sc-jRHJzp kqRVCO']")
    num_topics = int(num_topics.text.split(" ")[0])

    cnt = 0
    while True:

        topics = driver.find_elements_by_xpath(
            "//*[@id='site-content']/div[2]/div/div[2]/div/div[2]/a"
        )
        ActionChains(driver).move_to_element(topics[-1]).perform()

        if len(topics) == num_topics:
            break
        if cnt > 100:
            sys.exit()

    di = {"url": [], "title": [], "created_date": [], "last_comment": [], "num_comments": []}
    for topic in topics:

        di["url"].append(
            topic.get_attribute("href"),
        )
        di["title"].append(
            topic.find_element_by_xpath("div/div[3]/div[1]/p").text,
        )
        di["created_date"].append(
            topic.find_element_by_xpath("div/div[3]/div[2]/p/span").get_attribute("title"),
        )
        di["last_comment"].append(
            topic.find_element_by_xpath("div/div[4]/div[1]/p/p/a/span[2]").get_attribute("title"),
        )
        di["num_comments"].append(
            topic.find_element_by_xpath("div/div[4]/div[2]/p").text,
        )

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
