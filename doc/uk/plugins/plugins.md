> **Мова / Language:** Українська | [English full tutorial](../../plugins/plugins.md)

Посібник з плагінів Codimension
===============================

У цьому посібнику розглянуто дві теми: як реалізована підтримка плагінів у
Codimension і як написати простий плагін, використовуючи доступні API.

Реалізація підтримки плагінів
-----------------------------

Найкоротша відповідь на питання «що таке плагін Codimension?»: це Python-клас,
реалізований певним чином. Codimension написано на Python, тому плагіни теж
мають бути на Python.

Перед деталями — термінологія, яку Codimension використовує для плагінів.

### Розташування плагінів

При старті Codimension шукає плагіни в двох місцях:

1. `/usr/share/codimension3-plugins/`
2. Каталог `.codimension3/plugins` у домашній директорії користувача
   (на Linux зазвичай `~/.codimension3/plugins`)

Рекомендується, щоб кожен плагін займав окремий каталог з усіма потрібними
файлами. Структура може виглядати так:

~~~
/usr/share/codimension3-plugins/plugin1/...
                                 plugin2/...
                                 plugin3/...

~/.codimension3/plugins/plugin4/...
                                  plugin5/...
                                  plugin6/...
~~~

Залежно від розташування плагіни діляться на **системні** (system wide) та
**користувацькі** (user). У прикладі вище `plugin1`–`plugin3` — системні,
`plugin4`–`plugin6` — користувацькі.

У віртуальному середовищі Codimension також шукає плагіни в
`site-packages/cdmplugins/`.

### Вбудовані плагіни

Туди встановлюються плагіни, що постачаються з Codimension:

| Плагін | Гаряча клавіша / примітка |
|--------|---------------------------|
| **Ruff** | Ctrl+Shift+R |
| **Mypy** | Ctrl+Shift+M |
| **Pytest** | Ctrl+Shift+T |
| **Coverage** | Ctrl+Shift+C |
| **Bandit** | Ctrl+Shift+B |
| **pip-audit** | Ctrl+Shift+A |
| **Ruff format** | Ctrl+Shift+F (format-on-save у конфігурації) |
| **TODO panel** | Ctrl+Shift+O |
| **Git** | VCS: status, commit, push, pull, add, branch, Create PR, View PRs; GitHub token у Settings |

Драйвери Ruff, Bandit і Mypy використовують базовий клас `LintDriverBase`
(`cdmplugins/lintdriverbase.py`).

### Ім'я, версія, стан

Ім'я та версія плагіну зберігаються у файлі опису (`.cdmp`), який ініціює
завантаження.

Кожен плагін може бути **увімкнений** або **вимкнений** (activated/deactivated).
При завантаженні всі плагіни спочатку вважаються увімкненими; новий плагін
активується автоматично на наступному старті.

Автоматичне вирішення конфліктів:

- якщо є системний і користувацький плагін з однаковим ім'ям — перемагає
  користувацький;
- якщо два плагіни одного типу (обидва user або обидва system) з однаковим
  ім'ям — перемагає вища версія;
- якщо імена, версії та розташування збігаються — перемагає довільний.

Плагін також вимикається автоматично, якщо не реалізує потрібний інтерфейс.

**Важливо:** незалежно від стану увімкнення/вимкнення екземпляр класу плагіну
створюється і залишається в пам'яті до закриття IDE.

Керування станами — через **Options → Plugin Manager**. Плагін може
перемикатися між увімкненим і вимкненим станом довільну кількість разів за
сесію.

![Менеджер плагінів](../../plugins/pluginmanager.png "Менеджер плагінів")

### Категорії плагінів

Плагіни потребують різної підтримки з боку IDE; **категорія** визначає варіант
інтерфейсу між Codimension і плагіном. Категорії — це готові базові класи;
кожен плагін має успадковувати один із них.

На момент написання (Codimension v.4.11+) підтримуються:

- `WizardInterface` — `codimension/plugins/categories/wizardiface.py`
- `VersionControlSystemInterface`

Нові категорії з'являтимуться в `codimension/plugins/categories/`.

Базовий клас `CDMPluginBase` (`codimension/plugins/categories/cdmpluginbase.py`)
спрощує доступ до основних об'єктів IDE:

~~~python
if self.ide.project.isLoaded():
    # проєкт завантажено
    ...
else:
    # редагування окремих файлів
    ...
~~~

Доступ до об'єктів IDE — через `self.ide. ...` (повний список у `IDEAccess`).

Ієрархія також містить yapsy `IPlugin` і PyQt `QObject` для сигналів:

~~~python
self.ide.project.projectChanged.connect(self.__onProjectChanged)
~~~

![Базові класи плагінів](../../plugins/pluginbases.png "Базові класи плагінів")

Файли плагіну
-------------

Рекомендована структура каталогу плагіну:

~~~
~/.codimension3/plugins/pdfexporter/pdfexporter.cdmp
                                            __init__.py
                                            util_functions.py
                                            config_dialog.py
~~~

Codimension шукає файли з розширенням `.cdmp`. Приклад вмісту:

~~~ini
[Core]
Name = PDF exporter
Module = .

[Documentation]
Author = Mike Slartibartfast <mike.slartibartfast@some.com>
Version = 1.0.0
Website = http://mike.slartibartfast.homelinux.com/pdfexporter
Description = Codimension PDF exporter plugin
License = GPL v.3
~~~

- `[Core].Name` — довільний рядок, краще короткий.
- `[Core].Module` — шлях до модуля плагіну; рекомендовано `.` (поточний каталог).
- Секція `[Documentation]` — відображається в **Detailed information** менеджера
  плагінів.

Клас плагіну (`PDFExporterPlugin` у прикладі) **має** бути в `__init__.py` і
успадковувати категорійний базовий клас (наприклад, `WizardInterface`).
Розробник не змінює інші класи з діаграми ієрархії.

Імпорт модулів плагіну без relative import:

~~~python
import config_dialog
from util_functions import designCoastline
~~~

Модулі Codimension доступні плагіну:

~~~python
from utils.pixmapcache import PixmapCache
codimensionLogo = PixmapCache().getPixmap('logo.png')
~~~

Codimension використовує [yapsy](http://yapsy.sourceforge.net/) для підсистеми
плагінів.

Приклад: плагін Garbage Collector
---------------------------------

**Ідея:** збирач сміття Python викликає `gc.collect()` у передбачувані моменти:

- закриття вкладки;
- зміна проєкту;
- появa або видалення файлів у проєкті.

Результат (кількість зібраних об'єктів) показується згідно з налаштуванням:
log, status bar або нікуди.

### Створення каталогу та опису

~~~shell
mkdir garbagecollector
cd garbagecollector
~~~

Файл `garbagecollector.cdmp`:

~~~ini
[Core]
Name = Garbage collector
Module = .

[Documentation]
Author = Sergey Satskiy <sergey.satskiy@gmail.com>
Version = 1.0.0
Website = http://codimension.org
Description = Codimension garbage collector plugin
License = GPL v.3
~~~

### Клас плагіну

~~~python
from plugins.categories.wizardiface import WizardInterface

class GCPlugin(WizardInterface):
    def __init__(self):
        WizardInterface.__init__(self)
        return
~~~

`__init__` не робить важких ініціалізацій — усі плагіни інстанціюються при
старті.

Обов'язкові методи:

~~~python
    @staticmethod
    def isIDEVersionCompatible(ideVersion):
        return True

    def activate(self, ideSettings, ideGlobalData):
        WizardInterface.activate(self, ideSettings, ideGlobalData)
        self.__where = self.__getConfiguredWhere()
        self.ide.editorsManager.tabClosed.connect(self.__collectGarbage)
        self.ide.project.projectChanged.connect(self.__collectGarbage)

    def deactivate(self):
        self.ide.project.projectChanged.disconnect(self.__collectGarbage)
        self.ide.editorsManager.tabClosed.disconnect(self.__collectGarbage)
        WizardInterface.deactivate(self)
~~~

**Важливо:** у `activate` спочатку викликати базовий `activate`; у
`deactivate` — базовий `deactivate` останнім.

### Конфігурація

Діалог налаштувань (`configdlg.py`) — три радіокнопки: log, status bar, silent.

![Діалог конфігурації GC](../../plugins/gcconfigdialog.png "Діалог конфігурації GC")

~~~python
    def getConfigFunction(self):
        return self.configure

    def configure(self):
        dlg = GCPluginConfigDialog(self.__where)
        if dlg.exec_() == QDialog.Accepted:
            newWhere = dlg.getCheckedOption()
            if newWhere != self.__where:
                self.__where = newWhere
                self.__saveConfiguredWhere()
~~~

Налаштування зберігається в `gc.plugin.conf` (ini) у `self.ide.settingsDir`.

### Збір сміття

~~~python
    def __collectGarbage(self, ignored=None):
        iterCount = 0
        collected = 0
        currentCollected = gc.collect()
        while currentCollected > 0:
            iterCount += 1
            collected += currentCollected
            currentCollected = gc.collect()
        if self.__where == GCPluginConfigDialog.SILENT:
            return
        message = "Collected " + str(collected) + " objects in " + \
                  str(iterCount) + " iteration(s)"
        if self.__where == GCPluginConfigDialog.STATUS_BAR:
            self.ide.showStatusBarMessage(message, 5000)
        else:
            logging.info(message)
~~~

### Меню

Codimension надає чотири місця для пунктів меню плагіну:

- головне меню (під Plugin Manager);
- контекстне меню буфера редагування;
- контекстне меню файлу в проєкті;
- контекстне меню каталогу.

GC-плагін використовує лише головне меню:

~~~python
    def populateMainMenu(self, parentMenu):
        parentMenu.addAction("Configure", self.configure)
        parentMenu.addAction("Collect garbage", self.__collectGarbage)

    def populateFileContextMenu(self, parentMenu):
        return

    def populateDirectoryContextMenu(self, parentMenu):
        return

    def populateBufferContextMenu(self, parentMenu):
        return
~~~

Повний код прикладу:

- [`garbagecollector.cdmp`](https://github.com/SergeySatskiy/cdm-gc-plugin/blob/master/cdmplugins/gc/garbagecollector.cdmp)
- [`__init__.py`](https://github.com/SergeySatskiy/cdm-gc-plugin/blob/master/cdmplugins/gc/__init__.py)
- [`configdlg.py`](https://github.com/SergeySatskiy/cdm-gc-plugin/blob/master/cdmplugins/gc/configdlg.py)

Додатково
---------

**Друк і логування:** stdout → log (чорний), stderr → log (червоний);
`logging.info()` також у log. Опція `--debug` увімкнює debug-рівень.

**Globals і Settings:** при `activate` плагін отримує singleton-и глобальних
даних і налаштувань IDE. Неправильні зміни можуть призвести до падіння IDE.
`CDMPluginBase` спрощує доступ до найважливіших об'єктів.

---

Повний англомовний посібник з усіма деталями, додатковими прикладами та
розділом Miscellaneous: [English full tutorial](../../plugins/plugins.md).
