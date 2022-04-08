import time
import requests
import schedule

from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, InvalidElementStateException


# 支付密码
PAY_PASSWORD = ''
# 买菜成功 Bark 推送 (可选)
BARK_ID = ''


def init():
    desired_caps = dict(
        platformName='Android',
        platformVersion='9',
        ensureWebviewsHavePages=True,
        nativeWebScreenshot=True,
        unicodeKeyboard=True,
        resetKeyboard=True,
        newCommandTimeout=3600,
        noReset=True,
        automationName='uiautomator2',
        appPackage="com.yaya.zone",
        appActivity="cn.me.android.splash.activity.SplashActivity",
    )
    driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)

    # 跳过开屏广告
    time.sleep(0.5)
    try:
        driver.find_element(value='com.yaya.zone:id/tv_skip').click()
    except NoSuchElementException:
        pass

    # 进入购物车页面
    while True:
        try:
            time.sleep(1.0)
            driver.find_element(value='com.yaya.zone:id/ani_car').click()
            break
        except NoSuchElementException:
            continue

    return driver


def refresh(driver):
    try:
        actions = ActionChains(driver)
        actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, 'touch'))
        actions.w3c_actions.pointer_action.move_to_location(x=600, y=600)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.move_to_location(x=600, y=1500)
        actions.w3c_actions.pointer_action.release()
        actions.perform()
    except InvalidElementStateException:
        return


def cart(driver):
    # 防止异常返回，确保在购物车页
    try:
        driver.find_element(value='com.yaya.zone:id/ani_car').click()
    except (NoSuchElementException, StaleElementReferenceException):
        pass

    # 进入结算页面
    while True:
        try:
            driver.find_element(value='com.yaya.zone:id/btn_submit').click()
            time.sleep(0.2)
            elements = driver.find_elements(by=AppiumBy.CLASS_NAME, value='android.widget.TextView')
            if len(elements) > 0 and elements[0].get_attribute('text') == '确认订单':
                break

            elements = driver.find_elements(value='com.yaya.zone:id/tv_refresh')
            if len(elements) > 0:
                break

        except NoSuchElementException: # 购物车为空，刷新
            refresh(driver)


def order(driver):
    while True:
        # 等待进入
        elements = driver.find_elements(value='com.yaya.zone:id/tv_refresh')
        if len(elements) > 0:
            elements[0].click()
            continue

        # 取消优惠券，余额支付和优惠券不能共享
        # try:
        #     elements = driver.find_elements(value='com.yaya.zone:id/couponMessage') # tv_coupon_tick
        #     if len(elements) > 0 and elements[0].get_attribute('text') == '已选最大优惠':
        #         elements[0].click()
        #         time.sleep(0.2)
        #         checkbox_elements = driver.find_elements(by=AppiumBy.CLASS_NAME, value='android.widget.CheckBox')
        #         if len(checkbox_elements) > 0 and checkbox_elements[0].get_attribute('checked'):
        #             checkbox_elements[0].click()
        #         sure_elements = driver.find_elements(value='com.yaya.zone:id/tv_coupon_sure')
        #         if len(sure_elements) > 0:
        #             sure_elements[0].click()
        #         time.sleep(0.2)
        # except StaleElementReferenceException:
        #     pass

        # 立即支付
        try:
            pay_btns = driver.find_elements(value='com.yaya.zone:id/tv_submit')
            if len(pay_btns) > 0:
                pay_btns[0].click()
                continue # 连击
        except StaleElementReferenceException:
            continue

        # 输入密码
        elements = driver.find_elements(value='com.yaya.zone:id/passEditText')
        if len(elements) > 0:
            elements[0].send_keys(PAY_PASSWORD)
            continue

        # 缺货继续支付
        elements = driver.find_elements(value='com.yaya.zone:id/tv_goto_pay')
        if len(elements) > 0:
            # 商品金额
            money_elements = driver.find_elements(value='com.yaya.zone:id/tv_new_money')
            if len(money_elements) > 0:
                # 在此可以根据金额决定是否继续支付
                print(money_elements[0].get_attribute('text'))

            elements[0].click()
            continue

        # 下单失败
        elements = driver.find_elements(value='com.yaya.zone:id/button_one')
        if len(elements) > 0:
            elements[0].click()
            refresh(driver)
            return

        # 选择送达时间
        if len(driver.find_elements(value='com.yaya.zone:id/tv_dialog_select_time_title')) > 0:
            elements = driver.find_elements(value='com.yaya.zone:id/cl_item_select_hour_root')         
            for element in elements:
                # title = element.find_element(value='com.yaya.zone:id/tv_item_select_hour_title')
                desc = element.find_element(value='com.yaya.zone:id/tv_item_select_hour_desc')
                if desc.get_attribute('text') != '已约满':
                    element.click()
                    break
            else:
                # 预约时间已满
                driver.find_element(value='com.yaya.zone:id/iv_dialog_select_time_close').click()
                while True:
                    try:
                        driver.find_element(value='com.yaya.zone:id/iv_order_back').click()
                    except (NoSuchElementException, StaleElementReferenceException):
                        break
                refresh(driver)
                return

        # 支付成功
        elements = driver.find_elements(value='com.yaya.zone:id/tv_state_lable')
        elements = [e for e in elements if e.get_attribute('text') == '支付成功']
        if len(elements) > 0:
            if BARK_ID:
                requests.get(url = f'https://api.day.app/{BARK_ID}/叮咚买菜/买到了！' + '?sound=calypso&level=timeSensitive')
            exit()


def job():
    driver = init()
    # 每十次重新启动 App
    for _ in range(10):
        cart(driver)
        order(driver)
    driver.quit()


if __name__ == "__main__":
    # 准备六点时段
    schedule.every().day.at('05:55').do(job)

    while True:
        # 立即运行
        job()
        # 定时运行
        # schedule.run_pending()
        time.sleep(0.1)
