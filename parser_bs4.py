import time
import requests
from bs4 import BeautifulSoup
import datetime
import re
import asyncio
import aiohttp
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox
import pytest
import unittest

all_products = {}
count = 0
current_date = datetime.now().date()

# Создание базы данных и таблиц
def create_database():
    try:
        connection = sqlite3.connect('products.db')
        cursor = connection.cursor()
        cursor.execute("""PRAGMA foreign_keys = ON""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS selection (
                            selection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            date TEXT,
                            num_products INTEGER)""")
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                            id INTEGER PRIMARY KEY,
                            prod_selection_id INTEGER,
                            name TEXT,
                            price REAL,
                            FOREIGN KEY (prod_selection_id) REFERENCES selection(selection_id)ON UPDATE CASCADE)''')
        connection.commit()
        connection.close()
    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)

# Сохранение результатов в базу данных
def save_to_db(current_date, all_products, count):
    try:
        connection = sqlite3.connect('products.db')
        cursor = connection.cursor()

        cursor.execute("""INSERT INTO selection (date, num_products)
                        VALUES (?, ?)""", (current_date.strftime('%Y-%m-%d'), count))

        cursor.execute("""SELECT selection_id FROM selection""")
        sel_ids = cursor.fetchall()

        for i in range(1, count + 1):
            cursor.execute('''INSERT INTO products (prod_selection_id, name, price)
                            VALUES (?, ?, ?)''', (len(sel_ids), all_products[i]["name"], all_products[i]["price"]))
        connection.commit()
        connection.close()
    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)

# синхронный парсер
def sync_parser():
     global all_products, count
     url = "https://www.a1.by/ru/shop/c/watch"
     response = requests.get(url=url)
     soup = BeautifulSoup(response.text, "lxml")

     pages_count = int(soup.find("ul", class_="pagination-block").find_all("a")[-2].text)

     for page in range(0, pages_count):
          url = f"https://www.a1.by/ru/shop/c/watch?q=%3Arelevance&originalRootCategory=watch&page={page}"
          response = requests.get(url=url)
          soup = BeautifulSoup(response.text, "lxml")
          watchs_items = soup.find_all("div", class_="product-listing-box")
          
          for watch_data in watchs_items:
               count += 1
               try:
                    watch_title = watch_data.find("div", class_="product-search-item-title").text.strip()
               except:
                    watch_title = "Нет названия часов"
                    
               try:
                    price = watch_data.find("div", class_="product-listing-item-charges").find("div", class_="product-listing-item-charge one-time-charge").find("span", class_="price").find("span", class_="price-value").text.replace(",", ".")
                    watch_price = float(re.sub(r'\b\s+\b', '', price))
               except:
                    watch_price = 0
                    
               product = {"name": f"{watch_title}", "price": f"{watch_price}"}
               all_products[count] = product     
               
          print(f"Обработана {page + 1}/{pages_count}")
          time.sleep(1)

async def get_page_data(session, page):
     global all_products, count
     url = f"https://www.a1.by/ru/shop/c/watch?q=%3Arelevance&originalRootCategory=watch&page={page}"

     async with session.get(url=url) as response:
          response_text = await response.text()

          soup = BeautifulSoup(response_text, "lxml")

          watchs_items = soup.find_all("div", class_="product-listing-box")
          
          for watch_data in watchs_items:
               count += 1
               try:
                    watch_title = watch_data.find("div", class_="product-search-item-title").text.strip()
               except:
                    watch_title = "Нет названия часов"
                    
               try:
                    price = watch_data.find("div", class_="product-listing-item-charges").find("div", class_="product-listing-item-charge one-time-charge").find("span", class_="price").find("span", class_="price-value").text.replace(",", ".")
                    watch_price = float(re.sub(r'\b\s+\b', '', price))
               except:
                    watch_price = 0
                    
               product = {"name": f"{watch_title}", "price": f"{watch_price}"}
               all_products[count] = product     
               
          print(f"Обработал страницу {page}")
          time.sleep(1)

# ассинхронный парсер
async def async_parser():

     url = "https://www.a1.by/ru/shop/c/watch"

     async with aiohttp.ClientSession() as session:
          response = await session.get(url=url)
          soup = BeautifulSoup(await response.text(), "lxml")
          pages_count = int(soup.find("ul", class_="pagination-block").find_all("a")[-2].text)

          tasks = []

          for page in range(0, pages_count):
               task = asyncio.create_task(get_page_data(session, page))
               tasks.append(task)

          await asyncio.gather(*tasks)
          
# Интерфейс
def gui():
     def onselect(evt):
          for prod in product_tree.get_children():
               product_tree.delete(prod)
          try:
               id = int(selection_tree.item(selection_tree.focus())['values'][0])
               params = (id, )
               cursor.execute("SELECT id, name, price FROM products WHERE prod_selection_id = ?", params)
               product_data = cursor.fetchall()
               for row in product_data:
                    product_tree.insert('', 'end', values=row)
          except:
               return

     def async_parse():
        global all_products, count
        create_database()
        start_time = time.time()
        asyncio.run(async_parser())
        finish_time = time.time() - start_time
        tkinter.messagebox.showinfo(title=None, message="Время выполнения парсинга: " + str(finish_time) + " секунд")
        save_to_db(current_date, all_products, count)
        all_products = {}
        count = 0
        update_tables(product_tree, selection_tree)
     
     def sync_parse():
        global all_products, count
        create_database()
        start_time = time.time()
        sync_parser()
        finish_time = time.time() - start_time
        tkinter.messagebox.showinfo(title=None, message="Время выполнения парсинга: " + str(finish_time) + " секунд")
        save_to_db(current_date, all_products, count)
        all_products = {}
        count = 0
        update_tables(product_tree, selection_tree)
     
     # Создание окна
     root = tk.Tk()
     root.title("Таблицы товаров и зачислений")

     # Подключение к базе данных
     connection = sqlite3.connect('products.db')
     cursor = connection.cursor()

     # Создание и настройка таблицы товаров
     product_frame = ttk.Frame(root)
     product_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
     product_tree = ttk.Treeview(product_frame, columns=("ID", "Name", "Price"), show="headings")
     product_tree.heading("ID", text="ID")
     product_tree.heading("Name", text="Наименование")
     product_tree.heading("Price", text="Цена")
     product_tree.pack(fill=tk.BOTH, expand=True)

     # Создание и настройка таблицы зачислений
     selection_frame = ttk.Frame(root)
     selection_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)
     selection_tree = ttk.Treeview(selection_frame, columns=("Selection_ID", "Date", "Quantity"), show="headings")
     selection_tree.heading("Selection_ID", text="Номер отбора")
     selection_tree.heading("Date", text="Дата")
     selection_tree.heading("Quantity", text="Количество")
     selection_tree.pack(fill=tk.BOTH, expand=True)
     selection_tree.bind("<<TreeviewSelect>>", onselect)
     
     def update_tables(product_tree, selection_tree):
        connection = sqlite3.connect("products.db")
        cursor = connection.cursor()
        for prod in product_tree.get_children():
            product_tree.delete(prod)
        for select in selection_tree.get_children():
            selection_tree.delete(select)
        cursor.execute("SELECT selection_id, date, num_products FROM selection")
        selection_data = cursor.fetchall()
        for row in selection_data:
            selection_tree.insert('', 'end', values=row)

     def drop_bd():
        selection_tree.selection_remove(selection_tree.selection())
        cursor.execute('''DROP TABLE IF EXISTS selection''')
        cursor.execute('''DROP TABLE IF EXISTS products''')
        for prod in product_tree.get_children():
            product_tree.delete(prod)
        for select in selection_tree.get_children():
            selection_tree.delete(select)
            
     # Функция для отображения результатов тестов
     def show_test_results(test_results):
          result_window = tk.Toplevel(root)
          result_window.title("Результаты тестов")

          # Определение размеров окна и позиции по середине экрана
          window_width = 350
          window_height = 300  # Увеличено для лучшего отображения результатов
          screen_width = root.winfo_screenwidth()
          screen_height = root.winfo_screenheight()
          x_coordinate = (screen_width - window_width) // 2
          y_coordinate = (screen_height - window_height) // 2

          result_window.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

          # Создание текстового виджета для отображения результатов
          result_text = tk.Text(result_window, wrap=tk.WORD)
          result_text.pack(fill=tk.BOTH, expand=True)

          # Запись результатов тестов в текстовый виджет
          result_text.insert(tk.END, test_results)

     class TestWebScraping(unittest.TestCase):
          @pytest.mark.xfail
          def test_num_products(self):
               url = "https://www.a1.by/ru/shop/c/watch"
               response = requests.get(url=url)
               soup = BeautifulSoup(response.text, "lxml")
               
               num_products = int(soup.find("a", id="tabs-controls-link-item_4").text.split("(")[1].replace(")", ""))
               self.assertEqual(num_products, 92)
          
          def test_category(self):
               url = "https://www.a1.by/ru/shop/c/watch"
               response = requests.get(url=url)
               soup = BeautifulSoup(response.text, "lxml")
               
               category = soup.find("a", id="tabs-controls-link-item_4").text.split("(")[0].strip()
               self.assertEqual(category, "Умные часы")

          def test_name_company(self):
               url = "https://www.a1.by/ru/shop/c/watch"
               response = requests.get(url=url)
               soup = BeautifulSoup(response.text, "lxml")
               
               name_company = soup.find("div", class_="yCmsContentSlot footer-copyright-text").text.split(".")[0]
               self.assertEqual(name_company, "© 2024 Унитарное предприятие «А1»")

          def test_google_play_link(self):
               url = "https://www.a1.by/ru/shop/c/watch"
               response = requests.get(url=url)
               soup = BeautifulSoup(response.text, "lxml")
               
               link = soup.find("a", id="footermya1googleplay")
               same_link = link.get_attribute_list("href")
               self.assertEqual(same_link[0], "https://play.google.com/store/apps/details?id=by.a1.selfcare")

     # Функция для запуска тестов
     def run_tests():
          loader = unittest.TestLoader()
          suite = loader.loadTestsFromTestCase(TestWebScraping)
          test_runner = unittest.TextTestRunner(verbosity=2)
          test_result = test_runner.run(suite)

          # Формирование строки с результатами тестов
          total_tests = test_result.testsRun
          failed_tests = len(test_result.failures)
          errored_tests = len(test_result.errors)
          successful_tests = total_tests - failed_tests - errored_tests

          result_summary = f"Выполнено тестов: {total_tests}\n"
          result_summary += f"Успешно выполненные тесты: {successful_tests}\n"
          result_summary += f"Непрошедшие тесты: {failed_tests + errored_tests}\n\n"

          result_summary += "Подробные результаты:\n"

          # Собираем результаты для каждого теста
          test_methods = [method for method in dir(TestWebScraping) if method.startswith("test_")]
          for method in test_methods:
               if any(fail[0].id().split('.')[-1] == method for fail in test_result.failures):
                    result_summary += f"{method} : Не пройдено\n"
               elif any(error[0].id().split('.')[-1] == method for error in test_result.errors):
                    result_summary += f"{method} : Ошибка\n"
               else:
                    result_summary += f"{method} : Пройдено\n"

          show_test_results(result_summary)

     # Кнопка для обновления таблиц
     test_button = ttk.Button(root, text="Запустить тесты", command=run_tests)
     test_button.pack(side=tk.TOP, padx=10, pady=10)
     
     sync_button = ttk.Button(root, text="Синхронный парсинг", command=sync_parse)
     sync_button.pack(side=tk.BOTTOM, padx=10, pady=10)
     async_button = ttk.Button(root, text="Асинхронный парсинг", command=async_parse)
     async_button.pack(side=tk.BOTTOM, padx=10, pady=20)
     drop_button = ttk.Button(root, text="Очистить БД", command=drop_bd)
     drop_button.pack(side=tk.BOTTOM, padx=10, pady=20)
     
     # Обновление таблицы selection
     cursor.execute("SELECT selection_id, date, num_products FROM selection")
     selection_data = cursor.fetchall()
     for row in selection_data:
          selection_tree.insert('', 'end', values=row)
          
     # Центрирование текста в ячейках таблиц
     for tree in [product_tree, selection_tree]:
          for column in tree["columns"]:
               tree.heading(column, anchor="center")
               tree.column(column, anchor="center")

     root.mainloop()

def main():
     create_database()
     gui()
     save_to_db(current_date, all_products, count)

if __name__ == "__main__":
    main()