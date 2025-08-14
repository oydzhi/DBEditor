import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
    QMessageBox, QLineEdit, QLabel, QTableWidget, QTableWidgetItem, QInputDialog
)
from PyQt5.QtCore import Qt
import psycopg2

conn = None
curs = None

def check_fields(database, user, password, host, port):
    if not user.text():
        show_message("Ошибка!", "Введите имя пользователя")
        user.setStyleSheet("QLineEdit { border: 1px solid red; }")
        return
    user.setStyleSheet("QLineEdit { border: 1px solid black; }")

    if not password.text():
        show_message("Ошибка!", "Введите пароль от базы данных")
        password.setStyleSheet("QLineEdit { border: 1px solid red; }")
        return
    password.setStyleSheet("QLineEdit { border: 1px solid black; }")

    if not database.text():
        show_message("Ошибка!", "Введите имя базы данных")
        database.setStyleSheet("QLineEdit { border: 1px solid red; }")
        return
    database.setStyleSheet("QLineEdit { border: 1px solid black; }")

    if not host.text():
        show_message("Ошибка!", "Введите хост")
        host.setStyleSheet("QLineEdit { border: 1px solid red; }")
        return
    host.setStyleSheet("QLineEdit { border: 1px solid black; }")

    if not port.text():
        show_message("Ошибка!", "Введите порт")
        port.setStyleSheet("QLineEdit { border: 1px solid red; }")
        return
    port.setStyleSheet("QLineEdit { border: 1px solid black; }")

    connection(database.text(), user.text(), password.text(), host.text(), port.text())

def show_message(title, text):
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.exec()

def connection(database, user, password, host, port):
    global conn
    global curs
    try:
        conn = psycopg2.connect(database=database, user=user, password=password, host=host, port=port)
        curs = conn.cursor()
        connect_win.close()
        makeMainWindow()
    except (Exception, psycopg2.Error) as error:
        show_message("Ошибка!", f"Не удалось подключиться к базе данных\n{error}")

def get_tables(table_list):
    global curs
    curs.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    table_list.clear()
    for table in curs.fetchall():
        table_list.addItem(table[0])

def drop_table(table_list, table):
    global curs
    global conn
    if table_list.selectedItems():
        table_name = table_list.selectedItems()[0].text()
        try:
            curs.execute(f"DROP TABLE IF EXISTS {table_name};")
            conn.commit()

            show_message("Успех!", f"Таблица '{table_name}' успешно удалена.")
            table.setRowCount(0)
            table.setColumnCount(0)
            get_tables(table_list)
        except (Exception, psycopg2.Error) as error:
            conn.rollback()
            show_message("Ошибка!", f"Не удалось удалить таблицу:\n{error}")

def create_table(table_list, table):
    global curs
    global conn
    table_name, ok = QInputDialog.getText(main_win, 'Создать таблицу', 'Введите имя новой таблицы:')

    if not ok or not table_name:
        return

    if table_list.findItems(table_name, Qt.MatchExactly):
        show_message("Ошибка!", "Таблица с таким именем уже существует")
        return

    fields = []
    while True:
        field_name, ok = QInputDialog.getText(main_win, 'Создать таблицу', 'Введите имя поля (или оставьте пустым для завершения ввода):')
        if not ok or not field_name:
            break
        
        field_type, ok = QInputDialog.getItem(main_win, 'Выбор типа данных', 'Выберите тип данных:', ['INTEGER', 'VARCHAR(255)', 'BOOLEAN', 'DATE', 'TIMESTAMP'])
        if not ok or not field_type:
            break
        
        fields.append(f"{field_name} {field_type}")

    primary_key, ok = QInputDialog.getText(main_win, 'Создать таблицу', 'Введите имя первичного ключа:')
    if not ok or not primary_key:
        return

    fields_str = ", ".join(fields + [f"PRIMARY KEY ({primary_key})"])
    try:
        curs.execute(f"CREATE TABLE {table_name} ({fields_str});")
        conn.commit()

        show_message("Успех", f"Таблица '{table_name}' успешно создана.")
        get_tables(table_list)
        show_table(table_list, table)
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        show_message("Ошибка!", f"Не удалось создать таблицу:\n{error}")

def save_table(table_list, table):
    global curs
    global conn
    if table_list.selectedItems():
        table_name = table_list.selectedItems()[0].text()
        try:
            data = get_table_data(table)
            curs.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}'")
            columns = [name[0] for name in curs]

            curs.execute(f"DELETE FROM {table_name};")
            curs.executemany(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})", data)

            conn.commit()
            show_message("Успех", "Таблица успешно сохранена.")

        except (Exception, psycopg2.Error) as e:
            conn.rollback()
            show_message("Ошибка", f"Не удалось обновить таблицу: {str(e)}")

def rewrite_table(table_list, table):
    global curs
    global conn
    if table_list.selectedItems():
        table_name = table_list.selectedItems()[0].text()
        try:
            data = get_table_data(table)
            curs.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}'")
            columns = [name[0] for name in curs]
            curs.execute(f"DELETE FROM {table_name};")

            curs.executemany(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})", data)
            conn.commit()
            show_message("Успех!", "Таблица успешно перезаписана в базу данных")
        except psycopg2.DataError as e:
            conn.rollback()
        except (Exception, psycopg2.Error) as e:
            conn.rollback()
            show_message("Ошибка", f"Не удалось обновить таблицу: {str(e)}")
        finally:
            show_table(table_list, table)

def rename_table(table_list):
    global curs, conn
    if table_list.selectedItems():
        table_new_name, ok = QInputDialog.getText(main_win, 'Переименовать таблицу', 'Введите новое название таблицы:')
        table_name = table_list.selectedItems()[0].text()
        if ok and table_new_name:
            if table_list.findItems(table_new_name, Qt.MatchExactly):
                show_message("Ошибка!", "Таблица с таким именем уже существует")
                return
            try:
                curs.execute(f'ALTER TABLE {table_name} RENAME TO {table_new_name};')
                conn.commit()
                show_message("Успех!", f"Таблица успешно переименована. Новое название - {table_new_name}")
                get_tables(table_list)
            except (Exception, psycopg2.Error) as e:
                conn.rollback()
                show_message("Ошибка!", f"Не удалось переименовать таблицу: {str(e)}")

def show_table(table_list, widget):
    global curs
    widget.clear()
    if table_list.selectedItems():
        table_name = table_list.selectedItems()[0].text()
        curs.execute("SELECT indexdef FROM pg_indexes WHERE tablename = %s;", (table_name,))
        rows = curs.fetchone()
        primary_key = rows[0] if rows else ''
        curs.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns WHERE table_name='{table_name}'")
        columns = [name[0] +"\nprimary key\n" +name[1] if name[0] in primary_key else name[0] + "\n\n" +name[1] for name in curs]

        curs.execute(f"SELECT * FROM {table_name};")
        data = curs.fetchall()

        widget.setColumnCount(len(columns))
        widget.setRowCount(len(data))
        widget.setHorizontalHeaderLabels(columns)

        if data:
            for row_num, row_data in enumerate(data):
                for col_num, item in enumerate(row_data):
                    widget.setItem(row_num, col_num, QTableWidgetItem(str(item)))
        else:
            show_message(f"Информация о таблице {table_name}", "Таблица пустая")

def get_table_data(table):
    rows = table.rowCount()
    columns = table.columnCount()
    data = [
        tuple(table.item(row, col).text() if table.item(row, col) is not None else '' for col in range(columns))
        for row in range(rows)
    ]
    return data

def add_row(table):
    current_row = table.currentRow()
    table.insertRow(current_row + 1 if current_row >= 0 else table.rowCount())
def del_row(table, table_list):
    if table.rowCount() == 0:
        show_message("Ошибка", "Нет доступных строк для удаления.")
        return

    current_row = table.currentRow()
    table.removeRow(current_row if current_row != -1 else table.rowCount() - 1)
    rewrite_table(table_list, table)

def add_col(table, table_list):
    global curs
    global conn
    column_name, ok = QInputDialog.getText(main_win, 'Добавить столбец', 'Введите имя нового столбца:')
    if not ok or not column_name:
        return

    column_type, ok = QInputDialog.getItem(main_win, 'Выбор типа данных', 'Выберите тип данных для нового столбца:', ['INTEGER', 'VARCHAR(255)', 'BOOLEAN', 'DATE', 'TIMESTAMP'])
    if not ok or not column_type:
        return

    table.setHorizontalHeaderItem(table.columnCount() + 1, QTableWidgetItem(f"{column_name}\n\n{column_type.lower()}"))
    table_name = table_list.selectedItems()[0].text()
    try:
        curs.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};")
        conn.commit()
        show_message("Успех!", f"Столбец '{column_name}' типа '{column_type}' успешно добавлен в таблицу '{table_name}'.")
        show_table(table_list, table)
    except (Exception, psycopg2.Error) as e:
        conn.rollback()
        show_message("Ошибка", f"Не удалось добавить столбец: {str(e)}")
def del_col(table, table_list):
    global curs
    global conn
    current_column = table.currentColumn()

    if table.columnCount() == 0:
        show_message("Ошибка", "Нет доступных столбцов для удаления.")
        return

    if current_column == -1:
        current_column = table.columnCount() - 1

    column_name = table.horizontalHeaderItem(current_column).text().split('\n')[0]
    print(column_name)

    table.removeColumn(current_column)

    table_name = table_list.selectedItems()[0].text()

    try:
        curs.execute(f'ALTER TABLE "{table_name}" DROP COLUMN "{column_name}";')
        conn.commit()
        
        show_message("Успех!", f"Столбец '{column_name}' успешно удален из таблицы '{table_name}'.")
        rewrite_table(table_list, table)
    
    except (Exception, psycopg2.Error) as e:
        conn.rollback()
        show_message("Ошибка", f"Не удалось удалить столбец: {str(e)}")

def makeConnectionWindow():
    global connect_win
    connect_win = QWidget()
    connect_win.setWindowTitle("Database Editor by Bachurin Ivan")
    connect_win.resize(450, 250)

    username = QLineEdit()
    username_label = QLabel("Имя пользователя базы данных")

    password = QLineEdit()
    password.setEchoMode(QLineEdit.Password)
    password_label = QLabel("Пароль от базы данных")

    database = QLineEdit()
    database_label = QLabel("Название базы данных")

    host = QLineEdit()
    host_label = QLabel("Хост")

    port = QLineEdit()
    port_label = QLabel("Порт")

    button_submit = QPushButton("Подключиться")

    connect_layout = QVBoxLayout()
    connect_layout.addWidget(username_label, alignment=Qt.AlignLeft)
    connect_layout.addWidget(username)
    connect_layout.addWidget(password_label, alignment=Qt.AlignLeft)
    connect_layout.addWidget(password)
    connect_layout.addWidget(database_label, alignment=Qt.AlignLeft)
    connect_layout.addWidget(database)

    layoutH1 = QHBoxLayout()
    layoutH2 = QHBoxLayout()

    layoutH1.addWidget(host_label)
    layoutH1.addWidget(port_label)
    layoutH2.addWidget(host)
    layoutH2.addWidget(port)

    connect_layout.addLayout(layoutH1)
    connect_layout.addLayout(layoutH2)

    connect_layout.addWidget(button_submit)

    connect_win.setLayout(connect_layout)

    button_submit.clicked.connect(lambda: check_fields(database, username, password, host, port))

    connect_win.show()

def makeMainWindow():
    global main_win
    main_win = QWidget()
    main_win.setWindowTitle("Database Editor by Bachurin Ivan")
    main_win.resize(1000, 500)

    table_list_label = QLabel("Список доступных таблиц:")
    table_list = QListWidget()

    table_widget_label = QLabel("Содержимое таблицы:")
    table_widget = QTableWidget()

    button_create = QPushButton("Создать таблицу")
    button_save = QPushButton("Сохранить изменения")
    button_delete = QPushButton("Удалить таблицу")
    button_rename = QPushButton("Переименовать таблицу")

    row_add = QPushButton("Добавить строку")
    row_del = QPushButton("Удалить строку")
    col_add = QPushButton("Добавить столбец")
    col_del = QPushButton("Удалить столбец")

    buttons_row1 = QHBoxLayout()
    buttons_row2 = QHBoxLayout()

    buttons_row1.addWidget(row_add)
    buttons_row1.addWidget(row_del)
    buttons_row2.addWidget(col_add)
    buttons_row2.addWidget(col_del)

    layoutV1 = QVBoxLayout()
    layoutV2 = QVBoxLayout()
    layoutV3 = QVBoxLayout()

    layoutV1.addWidget(table_list_label)
    layoutV1.addWidget(table_list)
    layoutV1.addWidget(button_rename)

    layoutV2.addWidget(table_widget_label)
    layoutV2.addWidget(table_widget)
    layoutV2.addLayout(buttons_row1)
    layoutV2.addLayout(buttons_row2)

    layoutV3.addWidget(button_create)
    layoutV3.addWidget(button_save)
    layoutV3.addWidget(button_delete)

    main_layout = QHBoxLayout()
    main_layout.addLayout(layoutV1)
    main_layout.addLayout(layoutV2, stretch=2)
    main_layout.addLayout(layoutV3)

    main_win.setLayout(main_layout)
    main_layout.setSpacing(10)

    get_tables(table_list)

    table_list.itemClicked.connect(lambda: show_table(table_list, table_widget))
    button_delete.clicked.connect(lambda: drop_table(table_list,table_widget))
    button_create.clicked.connect(lambda: create_table(table_list, table_widget))
    button_save.clicked.connect(lambda: save_table(table_list, table_widget))
    button_rename.clicked.connect(lambda: rename_table(table_list))

    row_add.clicked.connect(lambda: add_row(table_widget))
    row_del.clicked.connect(lambda: del_row(table_widget, table_list))
    col_add.clicked.connect(lambda: add_col(table_widget, table_list)) 
    col_del.clicked.connect(lambda: del_col(table_widget, table_list)) 
    main_win.show()

app = QApplication([]) 
makeConnectionWindow() 
sys.exit(app.exec_())