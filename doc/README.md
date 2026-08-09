# Документація Codimension (форк)

> **Мова / Language:** [English](en/README.md) | Українська

**Активний репозиторій:** https://github.com/sesquicadaver/codimension  
**Версія:** 4.11.0 | **Python (CI):** 3.10–3.13 | **Встановлення:** з цього репозиторію ([INSTALL.md](INSTALL.md))

## Продуктова довідка (Help у IDE)

**Help → Documentation** відкриває:

- **[user/index.md](user/index.md)**

Установлений пакет містить лише користувацьку довідку з `doc/user/` та
пов’язані топіки функцій IDE. Індекси для контриб’юторів:

| Мова | Індекс |
| ---- | ------ |
| Українська | [uk/README.md](uk/README.md) |
| English | [en/README.md](en/README.md) |

Політика двомовності: [BILINGUAL.md](BILINGUAL.md).

Каталог `doc/www/` — архівне дзеркало старого сайту (не оновлюється).

---

## Швидкий старт (розробка)

| Документ | Зміст |
| -------- | ----- |
| [../README.md](../README.md) / [../README.en.md](../README.en.md) | Огляд проєкту |
| [INSTALL.md](INSTALL.md) / [en/INSTALL.md](en/INSTALL.md) | Встановлення |
| [../FORK.md](../FORK.md) / [../FORK.en.md](../FORK.en.md) | Зміни форку |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) / [../CONTRIBUTING.en.md](../CONTRIBUTING.en.md) | Внесення змін |
| [../ROADMAP.uk.md](../ROADMAP.uk.md) / [../ROADMAP.md](../ROADMAP.md) | Дорожній план |
| [../TODO_FIXME.md](../TODO_FIXME.md) / [../TODO_FIXME.en.md](../TODO_FIXME.en.md) | Відомі проблеми |
| [../ChangeLog](../ChangeLog) | Історія змін |

---

## Плагіни та CI (розробка)

| English | Українська |
| ------- | ---------- |
| [plugins/plugins.md](plugins/plugins.md) | [uk/plugins/plugins.md](uk/plugins/plugins.md) |
| [plugins/plugins-implementation-plan.md](plugins/plugins-implementation-plan.md) | [en/plugins/plugins-implementation-plan.md](en/plugins/plugins-implementation-plan.md) |
| [plugins/git-github-plugin-plan.md](plugins/git-github-plugin-plan.md) | — |
| [plugins/living-specification.md](plugins/living-specification.md) | [en/plugins/living-specification.md](en/plugins/living-specification.md) |
| [github-integration-plan.md](github-integration-plan.md) | [en/github-integration-plan.md](en/github-integration-plan.md) |
| [../NOTES.en.md](../NOTES.en.md) | [../NOTES.md](../NOTES.md) |

---

## Функціональність IDE

| English (канон) | Українська |
| --------------- | ---------- |
| [project/project.md](project/project.md) | [uk/project/project.md](uk/project/project.md) |
| [technology/technology.md](technology/technology.md) | [uk/technology/technology.md](uk/technology/technology.md) |
| [technology/parser-contract.md](technology/parser-contract.md) | [uk/technology/parser-contract.md](uk/technology/parser-contract.md) |
| [md/mdsupport.md](md/mdsupport.md) | [uk/md/mdsupport.md](uk/md/mdsupport.md) |
| [smartzoom/smartzoom.md](smartzoom/smartzoom.md) | [uk/smartzoom/smartzoom.md](uk/smartzoom/smartzoom.md) |
| [dependencies/dependencies.md](dependencies/dependencies.md) | [uk/dependencies/dependencies.md](uk/dependencies/dependencies.md) |
| [deadcode/deadcode.md](deadcode/deadcode.md) | [uk/deadcode/deadcode.md](uk/deadcode/deadcode.md) |
| [complexity/complexity.md](complexity/complexity.md) | [uk/complexity/complexity.md](uk/complexity/complexity.md) |
| [disassembling/disassembling.md](disassembling/disassembling.md) | [uk/disassembling/disassembling.md](uk/disassembling/disassembling.md) |
| [colorschemes/colorschemes.md](colorschemes/colorschemes.md) | [uk/colorschemes/colorschemes.md](uk/colorschemes/colorschemes.md) |
| [grouping/grouping.md](grouping/grouping.md) | [uk/grouping/grouping.md](uk/grouping/grouping.md) |
| [cml/cml.md](cml/cml.md) | [uk/cml/cml.md](uk/cml/cml.md) |
| [pyflakes/pyflakes.md](pyflakes/pyflakes.md) | [uk/pyflakes/pyflakes.md](uk/pyflakes/pyflakes.md) |
| [editorsettings/editorsettings.md](editorsettings/editorsettings.md) | [uk/editorsettings/editorsettings.md](uk/editorsettings/editorsettings.md) |

---

## Ліцензія

| Українська | English |
| ---------- | ------- |
| [LICENSE_COMPLIANCE.md](LICENSE_COMPLIANCE.md) | [en/LICENSE_COMPLIANCE.md](en/LICENSE_COMPLIANCE.md) |

---

## Оновлення документації

При зміні коду оновлюйте:

1. `ChangeLog`
2. Відповідний розділ у `doc/uk/` **та** `doc/en/` (або канонічний `doc/<topic>/`)
3. [plugins/living-specification.md](plugins/living-specification.md) та [en/plugins/living-specification.md](en/plugins/living-specification.md)
4. [../TODO_FIXME.md](../TODO_FIXME.md) та [../TODO_FIXME.en.md](../TODO_FIXME.en.md)
5. Продуктовий TOC [user/index.md](user/index.md), якщо змінюється користувацька довідка
