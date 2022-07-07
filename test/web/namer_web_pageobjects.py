from typing import List, Optional
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By


class NavElements():
    __failed: WebElement
    __queue: WebElement
    __config: WebElement

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href="./settings"]')))
        self.__failed: WebElement = self.__driver.find_element(by=By.CSS_SELECTOR, value='a[href="./failed"]')
        self.__queue: WebElement = self.__driver.find_element(by=By.CSS_SELECTOR, value='a[href="./queue"]')
        self.__config: WebElement = self.__driver.find_element(by=By.CSS_SELECTOR, value='a[href="./settings"]')

    def failed_page(self):
        self.__failed.click()
        return FailedPage(self.__driver)

    def queue_page(self):
        self.__queue.click()
        return QueuePage(self.__driver)

    def config_page(self):
        self.__config.click()
        return ConfigPage(self.__driver)


class SearchSelection():
    __driver: WebDriver
    __dismissal: WebElement
    __close: WebElement
    __items: List[WebElement]

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        self.__dismissal = self.__driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Close"]')
        self.__close = self.__driver.find_element(By.CSS_SELECTOR, 'button[data-bs-dismiss="modal"]')
        self.items = self.__driver.find_elements(By.CLASS_NAME, 'col m-1')

    def dismiss(self) -> 'FailedPage':
        self.__dismissal.click()
        return FailedPage(self.__driver)

    def close(self) -> 'FailedPage':
        self.__close.click()
        return FailedPage(self.__driver)

    def results(self) -> List:
        # todo result items
        return self.__items


class SearchInputModal():
    __driver: WebDriver
    __button_close: WebElement
    __search_input: WebElement
    __search_submit: WebElement
    __search_close: WebElement

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        self.__button_close = self.__driver.find_element(By.CSS_SELECTOR, 'button[aria-label="close"]')
        self.__search_input = self.__driver.find_element(By.ID, 'queryInput')
        self.__search_submit = self.__driver.find_element(By.CSS_SELECTOR, 'button[data-bs-dismiss="modal"]')
        self.__search_close = self.__driver.find_element(By.CSS_SELECTOR, 'button[data-bs-target="#searchResults"]')

    def dismiss(self) -> 'FailedPage':
        self.__button_close.click()
        return FailedPage(self.__driver)

    def close(self) -> 'FailedPage':
        self.__search_close.click()
        return FailedPage(self.__driver)

    def search(self, override_term: Optional[str]) -> SearchSelection:
        self.__search_close.click()
        if override_term:
            self.__search_input.send_keys(override_term)
        self.__search_submit.click()
        return SearchSelection(self.__driver)


class LogModal():
    __driver: WebDriver
    __close: WebElement
    __log_item: WebElement

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        self.__close = self.__driver.find_element(by=By.ID, value='refreshFiles')
        self.__log_item = self.__driver.find_element(by=By.ID, value='refreshFiles')

    def close(self) -> 'FailedPage':
        self.__close.click()
        return FailedPage(self.__driver)

    def log_text(self) -> str:
        return self.__log_item.text


class FailedItem():
    __parent: WebElement
    __file_name: WebElement
    __file_extension: WebElement
    __file_size: WebElement
    __button_show_log: WebElement
    __button_search_modal: WebElement
    __button_delete: WebElement

    def __init__(self, parent: WebElement):
        self.__parent = parent
        self.__file_name = self.__parent.find_element(By.CSS_SELECTOR, ':nth-child(1)')
        self.__file_extension = self.__parent.find_element(By.CSS_SELECTOR, ':nth-child(2)')
        self.__file_size = self.__parent.find_element(By.CSS_SELECTOR, ':nth-child(3)')
        self.__button_show_log = self.__parent.find_element(By.CSS_SELECTOR, 'button[title="Show Log"]')
        self.__button_search_modal = self.__parent.find_element(By.CSS_SELECTOR, 'button[title="Search"]')
        self.__button_delete = self.__parent.find_element(By.CSS_SELECTOR, 'button[title="Delete"]')

    def delete_item(self) -> 'FailedPage':
        self.__button_delete.click()
        return FailedPage(self.__parent.parent).refresh_items()

    def show_log_modal(self) -> LogModal:
        self.__button_show_log.click()
        return LogModal(self.__parent.parent)

    def show_search_modal(self) -> SearchInputModal:
        self.__button_search_modal.click()
        return SearchInputModal(self.__parent.parent)

    def file_name(self) -> str:
        return self.__file_name.text

    def file_extension(self) -> str:
        return self.__file_extension.text

    def file_size(self) -> str:
        return self.__file_size.text


class FailedPage():
    __driver = WebDriver
    __refresh: WebElement
    __search: WebElement
    __failed_table: WebElement
    __items: List[WebElement]

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        self.__refresh = self.__driver.find_element(by=By.ID, value='refreshFiles')
        self.__search = self.__driver.find_element(by=By.CSS_SELECTOR, value='input[type="search"]')
        self.__failed_table = self.__driver.find_element(by=By.CSS_SELECTOR, value='table[id="failed"]')
        self.__items = self.__driver.find_elements(by=By.CSS_SELECTOR, value='table[id="failed"] tbody tr')

    def navigate_to(self) -> NavElements:
        return NavElements(self.__driver)

    def refresh_items(self) -> 'FailedPage':
        self.__refresh.click()
        return FailedPage(self.__driver)

    def items(self) -> List[FailedItem]:
        return [FailedItem(item) for item in self.__items]

    def search(self, search_term: Optional[str]) -> 'FailedPage':
        if search_term:
            self.__search.send_keys(search_term)
        return FailedPage(self.__driver)


class QueuePage():
    __driver: WebDriver

    def __init__(self, driver: WebDriver):
        self.__driver = driver

    def navigate_to(self) -> NavElements:
        return NavElements(self.__driver)


class ConfigPage():
    __driver: WebDriver

    def __init__(self, driver: WebDriver):
        self.__driver = driver

    def navigate_to(self) -> NavElements:
        return NavElements(self.__driver)
