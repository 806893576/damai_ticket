from selenium import webdriver
from os.path import exists
import json
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class Damai(object):
    def __init__(self, satrt_url, ticket_url, nick_name, date, session, price, ticket_num, real_name):
        # 这里定义需要的各个参数
        # 后期单独定义一个config文件保存
        self.satrt_url = satrt_url  # 大麦官网首页
        self.ticket_url = ticket_url # 目标抢票页面
        self.nick_name = nick_name # 用于校验登陆成功
        self.date = date # 判断是否需要选择日期
        self.session = session # 选择想要去的场次
        self.price = price # 选择想要去的票价
        self.ticket_num = ticket_num # 想要买的票的张数
        self.real_name = real_name # 是否需要实名认证，切选择哪个实名认证人

        self.check_wait_time = 3 # 页面元素加载总等待时间
        self.refresh_wait_time = 0.3 # 页面元素等待刷新时间
        self.status = 0 # 标记抢票过程中的状态
        self.start_time = 0 # 开始抢票的时间
        self.end_time = 0 # 记录抢票结束时间
        self.num = 0 # 记录抢票次数
        self.circle_num = 0 # 记录缺货登记时刷新页面获取余票的次数
        self.add_did = 0 # 判断是否是有效的加票数
        # self.driver = webdriver.Chrome() # 这里不要初试话driver，否则会在程序刚开始就打开浏览器


    def get_cookies(self):
        self.driver = webdriver.Chrome() # 实例化一个浏览器
        self.driver.get(self.satrt_url) # 发送请求
        # 1、判断是否离开首页去往登陆页面
        print("--------请点击登陆--------")
        while self.driver.title.find('大麦网-全球演出赛事官方购票平台') != -1:
            time.sleep(1) # 如果找到了相关title，那么就循环等待
        # 2、判断是否登陆成功并离开登陆页面
        print("--------扫码进行登陆--------")
        while self.driver.title == "大麦登录":
            time.sleep(1)
        cookies = self.driver.get_cookies() # 获取登陆成功后返回的cookies
        with open("cookies.txt", "w", encoding="utf-8") as f:
            f.write(json.dumps(cookies))
        print("--------保存cookies成功--------")
        self.driver.quit() # 关闭获取cookies的页面


    def set_cookies(self):
        try:
            with open("cookies.txt", "r") as f:
                cookies = json.loads(f.read())
                for cookie in cookies:
                    cookie_dict = {
                        'domain': '.damai.cn',
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'expires': "",
                        'path': '/',
                        'httpOnly': False,
                        'HostOnly': False,
                        'Secure': False
                    }
                    # print(cookie_dict)
                    self.driver.add_cookie(cookie_dict) # 在浏览器中写入cookies的
            print("--------载入cookies成功--------")
            # 刷新页面，使浏览器上的cookies生效
            self.driver.refresh()
        except:
            print("--------读取cookies.txt失败--------")


    def confirm_login(self):
        # 判断购票网址类别
        try:
            if self.ticket_url.find("detail.damai.cn") != -1: # 后缀是detail.damai.cn
                # By中的XPATH对应的时elements种的xpath而不是源代码中的？
                check_nick_name = (By.XPATH, "/html/body/div[1]/div/div[3]/div[1]/a[2]/div")
            elif self.ticket_url.find("piao.damai.cn") != -1: # piao.damai.cn
                check_nick_name = (By.XPATH, "/html/body/div[1]/div/ul/li[2]/div/label/a[2]")
            # 等到查询check_nick_name中包括自己昵称时执行下一步，否则报错
            WebDriverWait(self.driver, self.check_wait_time, self.refresh_wait_time).until(
                EC.text_to_be_present_in_element(check_nick_name, self.nick_name)
            )
            self.status = 1
            print("--------登陆成功--------")
        except Exception as e:
            print(e)
            self.status = 0
            print("********登陆出错，请检查配置文件昵称或删除cookie.pkl后重试********")
            self.driver.quit()
    
        
    def login(self):
        # 1、判断是否本地存有cookies，没有进行获取
        if not exists("cookies.txt"):
            # 获取并储存登陆后的cookies.plk
            self.get_cookies()
        # 2、再次打开浏览器，配置浏览器属性
        options = webdriver.ChromeOptions() # 配置chrome启动属性,关闭图片加载
        prefs = {"profile.managed_default_content_settings.images":2}
        options.add_experimental_option("prefs",prefs)
        self.driver = webdriver.Chrome(options=options) # 打开配置后的浏览器
        # 3、打开购买票物对应的页面
        self.driver.get(self.ticket_url)
        print("--------打开目标票务页面成功--------")
        # 4、添加保存在本地的cookies到浏览器上
        self.set_cookies()
        # 5、确认登陆是否成功
        self.confirm_login()
        # self.driver.quit()


    def detail_choose_ticket(self):
        self.start_time = time.time()
        print("--------抢票开始--------")
        # 判断是否跳转到了title中包含了“确认订单的页面”，如果没有，进行抢票循环
        while self.driver.title.find("确认订单") == -1:
            self.num += 1
            # 1、判断是否需要选择日期
            if self.date != 0: # 有需要选的日期
                calender = WebDriverWait(self.driver, self.check_wait_time, self.refresh_wait_time).until(
                    # 等待页面缓冲直到出现class为"functional-calendar"的元素
                    EC.presence_of_element_located((By.CLASS_NAME, "functional-calendar"))
                )
                datelist = calender.find_elements_by_css_selector("[class='wh_content_item']") # 找到能选择的日期
                datelist = datelist[7:] # 前7个数据是‘周一’...‘周日’，需要剔除
                datelist[self.date - 1].click() # 选择点击需要选择的第x个日期

            # 2、获取所有可以选择的元素，根据差别分类
            chooses = self.driver.find_elements_by_class_name("perform__order__select")
            for choose in chooses:
                if choose.find_element_by_class_name("select_left").text == '场次':
                    ch_session = choose
                elif choose.find_element_by_class_name("select_left").text == '票档':
                    ch_price = choose

            # 3、获取并处理场次信息
            session_list = ch_session.find_elements_by_class_name("select_right_list_item")
            # print(session_list)
            print('可选场次数量为：{}'.format(len(session_list)))
            if len(self.session) == 1: # 处理需求场次仅为1
                session_one = session_list[self.session[0] -1].click()
            else:
                for i in self.session:
                    m = session_list[i - 1]
                    # 根据场次框上面的状态，
                    try:
                        n = m.find_element_by_class_name('presell').text
                    except:
                        m.click()
                        # print('1')
                        break
                    else:
                        if n == '无票':
                            continue
                        else:
                            m.click()
                            # print('2')
                            break
                    # print('3')
            # print('4')

            # 4、获取并处理票价信息
            # 这里首先点击下一页的时候需要缓冲一阵子让点击下一页之后的页面能够加载出来
            # time.sleep(0.5), 最好使用WebDriverWait,当出现表征价格特征class出现时在进行下一步
            WebDriverWait(self.driver, self.check_wait_time, self.refresh_wait_time).until(
                EC.presence_of_element_located((By.CLASS_NAME, "sku_item"))
            )
            price_list = ch_price.find_elements_by_class_name('select_right_list_item')
            # print(price_list)
            print('可选票档数量为：{}'.format(len(price_list)))
            if len(self.price) == 1:
                price_one = price_list[self.price[0] - 1].click()
            else:
                for i in self.price:
                    m = price_list[i - 1]
                    # 根据场次框上面的状态，
                    try:
                        n = m.find_element_by_class_name('notticket').text
                    except:
                        m.click()
                        # print('1')
                        break
                    else:
                        if n == '缺货登记': # 当状态是缺货登记的时候，跳过
                            # print('2')
                            print("===缺货登记状态，刷新页面等待===")
                            continue
                        else:
                            m.click()
                            # print('3')
                            break

            def add_ticket():
                try:
                    for i in range(self.ticket_num - 1):
                        add_btn = WebDriverWait(self.driver, self.check_wait_time, self.refresh_wait_time).until(
                            EC.presence_of_element_located((By.XPATH, "//div[@class='cafe-c-input-number']/a[2]")))
                        # add_btn.click()
                        # 查询看是否连续两次出现了无法上加的class表明click失效
                        time.sleep(0.5)
                        add_btn_class = add_btn.get_attribute("class")
                        # print(add_btn_class)
                        if re.search('cafe-c-input-number-handler-disabled', add_btn_class):
                            self.add_did += 1

                        # 先判断当前class，再点，如果self.add_did>0,说明有下一页无效
                        add_btn.click()
                    # print(self.add_did)
                except:
                    raise Exception("******错误：票数增加失败******")

            # 5、选择完成后，根据确定购买按钮字样进行操作
            tobuybtn = self.driver.find_element_by_class_name("buybtn")
            tobuybtn_text = tobuybtn.text
            print(tobuybtn_text)
            if tobuybtn_text == "即将开抢" or tobuybtn_text == "即将开售":
                self.status = 2
                self.driver.refresh()
                print("===抢票尚未开始，刷新页面等待===")
                continue

            elif tobuybtn_text == "立即预订" or tobuybtn_text == "立即购买":
                add_ticket()
                if self.add_did >= 1:
                    self.status = 2
                    self.add_did = 0
                    self.driver.refresh()
                    print("===剩余票数小于您需要的票数，刷新页面等待，或control+c停止===")
                    continue
                else:
                    tobuybtn.click()
                    self.status = 3

            elif tobuybtn_text == "选座购买": # 选座购买暂时无法完成
                self.status = 4
                tobuybtn.click()
                print("******无法自动选座，请手动选座位******")
                break

            elif tobuybtn_text == "提交缺货登记":
                self.circle_num += 1
                if self.circle_num <= 100:
                    self.driver.refresh()
                    print("******票量不足，刷新重试，您可随时按住control+c停止循环******")
                    continue
                else:
                    print("******获取余票更新已经100次，退出循环******")
                    break



    def detail_check_order(self):
        print("--------确认订单进行中--------")
        # 校验是否抢到票的数量为自己需要的数量（可能出现click加按钮超出能买最大数量）
        if self.status == 3:
            # 需要实名认证时，id="confirmOrder_1"下有9个div，不需要有8个div
            if self.real_name:
                btn_div = 9
                print("--------正在选择购票人--------")
                try:
                    choose_xpath = '//*[@id="confirmOrder_1"]/div[2]/div[2]/div[1]/div[{}]/label/span[1]/input'
                    for i in self.real_name:
                        WebDriverWait(self.driver, self.check_wait_time, self.refresh_wait_time).until(
                            EC.presence_of_element_located((By.XPATH, choose_xpath.format(i)))
                        ).click()
                except Exception as e:
                    print(e)
                    raise Exception("******勾选实名认证失败，请核对实名要求及信息******")
            else:
                btn_div = 8
            # print(btn_div)
            button_xpath = '//*[@id="confirmOrder_1"]/div[{}]/button' # 同意以上协议并提交订单Xpath
            submitbtn = WebDriverWait(self.driver, self.check_wait_time, self.refresh_wait_time).until(
                EC.presence_of_element_located((By.XPATH, button_xpath.format(btn_div)))
            )
            print("--------点击提交订单--------")
            submitbtn.click()


    def finish(self):
        try:
            WebDriverWait(self.driver, self.check_wait_time, self.refresh_wait_time).until(
                EC.title_contains('支付宝'))
            print('--------订单提交成功--------')
            self.status = 5
            self.end_time = time.time()
        except Exception as e:
            print('******提交订单失败,请查看问题******')
            print(e)
        if self.status == 5:
            print("=======> 经过%d轮，耗时%f秒，抢票成功！请确认订单信息 <======" % (self.num, round(self.end_time - self.start_time, 3)))
        else:
            self.driver.quit()



if __name__ == '__main__':
    try:
        with open('./config.json', 'r') as f:
            config = json.loads(f.read())
        # 传入相关参数
        damai_ticket = Damai(config["satrt_url"], config["ticket_url"], config["nick_name"], config["date"], 
                        config["session"], config["price"], config["ticket_num"], config["real_name"])
    except:
        print("******获取初始数据失败，请检查config.json中的配置******")
    else:
        while True:
            if damai_ticket.status != 5:
                # damai_ticket = Damai()
                damai_ticket.login()
                damai_ticket.detail_choose_ticket()
                damai_ticket.detail_check_order()
                damai_ticket.finish()
                time.sleep(2) # 失败后，休眠2秒重新开始
            else:
                print("恭喜您抢票完成!!!!!!")
                break
        
            
            
            
    

    