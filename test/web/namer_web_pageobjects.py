from typing import Generic, List, Optional, TypeVar

from assertpy import assert_that, fail
from assertpy.assertpy import AssertionBuilder
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

T = TypeVar("T")


class Assertion(Generic[T], AssertionBuilder):
    def __init__(self, page_object: T, target):
        self.target = target
        self.page_object: T = page_object
        self.assertion_builder = assert_that(target)

    def on_success(self) -> T:
        return self.page_object

    def __getattr__(self, attr):
        out = getattr(self.assertion_builder, attr)
        if out == self.assertion_builder:
            return self
        else:
            return out


class NavElements:
    __failed: WebElement
    __queue: WebElement
    __config: WebElement

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        # wait until loaded
        self.__config = waitForAndFind(driver, By.CSS_SELECTOR, value='a[href="./settings"]')
        self.__failed: WebElement = self.__driver.find_element(by=By.CSS_SELECTOR, value='a[href="./failed"]')
        self.__queue: WebElement = self.__driver.find_element(by=By.CSS_SELECTOR, value='a[href="./queue"]')

    def failed_page(self):
        self.__failed.click()
        waitUntilInvisible(self.__config)
        return FailedPage(self.__driver)

    def queue_page(self):
        self.__queue.click()
        waitUntilInvisible(self.__config)
        return QueuePage(self.__driver)

    def config_page(self):
        self.__config.click()
        waitUntilInvisible(self.__config)
        return ConfigPage(self.__driver)


class SearchSelectionItem:
    __parent: WebElement
    __show: WebElement
    __select: WebElement
    __date: WebElement
    __title: WebElement

    def __init__(self, parent: WebElement):
        self.__parent = parent

        self.__title = waitForAndFind(self.__parent, By.CLASS_NAME, 'card-title')
        if self.__title.text is None or self.__title.text == "":
            waitUntilPresent(self.__parent.parent, By.CSS_SELECTOR, 'button[class="btn btn-primary float-end rename"]')
            self.__title = self.__parent.find_element(By.CLASS_NAME, 'card-title')
        self.__date = self.__parent.find_element(By.CLASS_NAME, 'card-text')
        self.__show = self.__parent.find_element(By.CSS_SELECTOR, 'a[class="btn btn-secondary"]')
        self.__select = self.__parent.find_element(By.CSS_SELECTOR, 'button[class="btn btn-primary float-end rename"]')

    def title_text(self) -> Assertion['SearchSelectionItem']:
        return Assertion(self, self.__title.text)

    def date_text(self) -> Assertion['SearchSelectionItem']:
        return Assertion(self, self.__date.text)

    def show(self) -> 'SearchSelectionItem':
        self.__show.click()
        return self

    def select(self) -> 'FailedPage':
        self.__select.click()
        waitUntilInvisible(self.__select)
        return FailedPage(self.__parent.parent).refresh_items()


class SearchSelection:
    __driver: WebDriver
    __cancel: WebElement
    __close: WebElement
    __items: List[WebElement]

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        self.__cancel = self.__driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Close"]')
        self.__close = self.__driver.find_element(By.CSS_SELECTOR, 'div[class="modal-footer"] button[class="btn btn-secondary"]')
        findAndWaitUntilStale(driver, By.ID, "progressBar")
        self.__items = waitForAndFindAll(driver, By.CSS_SELECTOR, 'div[class="card h-100"]')

    def cancel(self) -> 'FailedPage':
        self.__cancel.click()
        return FailedPage(self.__driver)

    def close(self) -> 'FailedPage':
        self.__close.click()
        return FailedPage(self.__driver)

    def results(self) -> List[SearchSelectionItem]:
        return [SearchSelectionItem(item) for item in self.__items]


class SearchInputModal:
    __driver: WebDriver
    __cancel: WebElement
    __search_input: WebElement
    __search_submit: WebElement
    __search_close: WebElement

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        self.__search_submit = waitForAndFind(driver, By.CSS_SELECTOR, 'button[data-bs-target="#searchResults"]')
        self.__cancel = waitForAndFind(driver, By.CSS_SELECTOR, 'button[aria-label="Close"]')
        self.__search_input = waitForAndFind(driver, By.ID, 'queryInput')
        self.__search_close = waitForAndFind(driver, By.CSS_SELECTOR, 'button[class="btn btn-secondary"]')

    def dismiss(self) -> 'FailedPage':
        self.__cancel.click()
        return FailedPage(self.__driver)

    def close(self) -> 'FailedPage':
        self.__search_close.click()
        return FailedPage(self.__driver)

    def search(self, override_term: Optional[str] = None) -> SearchSelection:
        if override_term:
            self.__search_input.clear()
            self.__search_input.send_keys(override_term)

        self.__search_submit.click()
        waitUntilInvisible(self.__search_submit)
        return SearchSelection(self.__driver)


class LogModal:
    __driver: WebDriver
    __close: WebElement
    __log_item: WebElement

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        wait = WebDriverWait(driver, 10)
        wait.until(expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, 'button[class="btn btn-secondary"]')))
        self.__close = self.__driver.find_element(By.CSS_SELECTOR, 'button[data-bs-dismiss="modal"]')
        self.__cancel = self.__driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Close"]')
        self.__log_item = self.__driver.find_element(By.CSS_SELECTOR, value='pre code')

    def close(self) -> 'FailedPage':
        self.__close.click()
        waitUntilInvisible(self.__close)
        return FailedPage(self.__driver)

    def log_text(self) -> Assertion['LogModal']:
        return Assertion(self, self.__log_item.text)


class FailedItem:
    __parent: WebElement
    __file_name: WebElement
    __file_extension: WebElement
    __file_size: WebElement
    __button_show_log: WebElement
    __button_search_modal: WebElement
    __button_delete: WebElement

    def __init__(self, parent: WebElement):
        self.__parent = parent
        self.__button_search_modal = waitForAndFind(self.__parent, By.CSS_SELECTOR, 'button[title="Search"]')
        self.__button_show_log = waitForAndFind(self.__parent, By.CSS_SELECTOR, 'button[title="Show Log"]')
        self.__button_delete = waitForAndFind(self.__parent, By.CSS_SELECTOR, 'button[title="Delete"]')
        self.__file_name = waitForAndFind(self.__parent, By.CSS_SELECTOR, ':nth-child(1)')
        self.__file_extension = waitForAndFind(self.__parent, By.CSS_SELECTOR, ':nth-child(2)')
        self.__file_size = waitForAndFind(self.__parent, By.CSS_SELECTOR, ':nth-child(3)')

    def delete_item(self) -> 'FailedPage':
        self.__button_delete.click()
        return FailedPage(self.__parent.parent).refresh_items()

    def show_log_modal(self) -> LogModal:
        self.__button_show_log.click()
        return LogModal(self.__parent.parent)

    def show_search_modal(self) -> SearchInputModal:
        self.__button_search_modal.click()
        return SearchInputModal(self.__parent.parent)

    def file_name(self) -> Assertion['FailedItem']:
        return Assertion(self, self.__file_name.text)

    def file_extension(self) -> Assertion['FailedItem']:
        return Assertion(self, self.__file_extension.text)

    def file_size(self) -> Assertion['FailedItem']:
        return Assertion(self, self.__file_size.text)


def waitForAndFind(driver, by: str, value: str) -> WebElement:
    wait = WebDriverWait(driver, 20)
    wait.until(expected_conditions.visibility_of_any_elements_located((by, value)))
    return driver.find_element(by, value)


def waitForAndFindAll(driver, by: str, value: str) -> List[WebElement]:
    wait = WebDriverWait(driver, 20)
    wait.until(expected_conditions.presence_of_element_located((by, value)))
    return driver.find_elements(by, value)


def findIfPresent(driver, by: str, value: str) -> Optional[WebElement]:
    return next(iter(driver.find_elements(by, value)), None)


def waitUntilPresent(driver, by: str, value: str) -> Optional[WebElement]:
    wait = WebDriverWait(driver, 20)
    wait.until(expected_conditions.visibility_of_any_elements_located((by, value)))


def findAndWaitUntilStale(driver, by: str, value: str):
    wait = WebDriverWait(driver, 20)
    element = findIfPresent(driver, by, value)
    if element:
        wait.until(expected_conditions.any_of(
            expected_conditions.invisibility_of_element(element),
            expected_conditions.staleness_of(element)))


def waitUntilInvisible(element: WebElement):
    if element:
        wait = WebDriverWait(element.parent, 20)
        wait.until(expected_conditions.any_of(
            expected_conditions.invisibility_of_element(element),
            expected_conditions.staleness_of(element)))


class FailedPage:
    __driver: WebDriver
    __refresh: WebElement
    __search: Optional[WebElement]
    __noFailedFiles: Optional[WebElement]
    __items: List[WebElement]
    __page_links: List[WebElement]

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        findAndWaitUntilStale(driver, By.ID, "progressBar")
        self.__refresh = waitForAndFind(driver, By.ID, 'refreshFiles')
        self.__noFailedFiles = findIfPresent(driver, By.CSS_SELECTOR, 'div[class="col m-1 text-center"] span')
        if self.__noFailedFiles is None:
            self.__page_links = waitForAndFindAll(driver, by=By.CSS_SELECTOR, value='a[class="page-link"]')
            self.__search = waitForAndFind(driver, by=By.CSS_SELECTOR, value='input[type="search"]')
            waitForAndFind(driver, by=By.CSS_SELECTOR, value='table[id*="failed"] tbody')
            self.__items = waitForAndFindAll(driver, by=By.CSS_SELECTOR, value='table[id*="failed"] tbody tr')

    def navigate_to(self) -> NavElements:
        return NavElements(self.__driver)

    def refresh_items(self) -> 'FailedPage':
        self.__refresh.click()
        return FailedPage(self.__driver)

    def items(self) -> List[FailedItem]:
        return [FailedItem(item) for item in self.__items]

    def assert_has_no_files(self) -> 'FailedPage':
        assert_that(self.__noFailedFiles).is_not_none()
        return self

    def search(self, search_term: Optional[str]) -> 'FailedPage':
        if not self.__search:
            fail("no search item on page, happens on purpose if there are no items")
        else:
            if search_term:
                self.__search.send_keys(search_term)
            return FailedPage(self.__driver)


class QueuePage:
    __driver: WebDriver
    __refresh: WebElement

    def __init__(self, driver: WebDriver):
        self.__driver = driver
        self.__refresh = self.__driver.find_element(by=By.ID, value='refreshFiles')

    def navigate_to(self) -> NavElements:
        return NavElements(self.__driver)


class ConfigPage:
    __driver: WebDriver

    def __init__(self, driver: WebDriver):
        self.__driver = driver

    def navigate_to(self) -> NavElements:
        return NavElements(self.__driver)
