import time
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

options = Options()
options.add_argument("--headless")
executable_path = "/usr/local/bin/chromedriver"
driver = webdriver.Chrome(chrome_options=options, executable_path=executable_path)
driver.implicitly_wait(1)
driver.get("https://www.kaggle.com/c/cassava-leaf-disease-classification/discussion")


num_topics = driver.find_element_by_xpath("//div[@class='sc-kIpgsX cRxfVQ sc-jRHJzp kqRVCO']")
num_topics = int(num_topics.text.split(" ")[0])


for _ in range(1000):

    topics = driver.find_elements_by_xpath(
        "//*[@id='site-content']/div[2]/div/div[2]/div/div[2]/a"
    )
    time.sleep(3)
    ActionChains(driver).move_to_element(topics[-1]).perform()

    if len(topics) == num_topics:
        break


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
        topic.find_element_by_xpath("div/div[4]/div[1]/p/p/a/span[2]").get_attribute("title")
    )
    di["num_comments"].append(
        topic.find_element_by_xpath("div/div[4]/div[2]/p").text,
    )

df = pd.DataFrame.from_dict(di)
df["created_date"] = df["created_date"].apply(
    lambda x: x.replace(" GMT+0900 (Japan Standard Time)", "")
)
df["created_date"] = df["created_date"].apply(
    lambda x: datetime.strptime(x, "%a %b %d %Y %H:%M:%S")
)

df["last_comment"] = df["last_comment"].apply(
    lambda x: x.replace(" GMT+0900 (Japan Standard Time)", "")
)
df["last_comment"] = df["last_comment"].apply(
    lambda x: datetime.strptime(x, "%a %b %d %Y %H:%M:%S")
)

df.to_csv("discussion.csv", index=False)
