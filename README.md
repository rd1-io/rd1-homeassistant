# RD1 для Home Assistant

Локальная интеграция контроллеров RD1 (вентиляция, сауны) с Home Assistant.
Работает на control unit по LAN — LCD-панель не нужна, ключ ESPHome не нужен.

Сущности приходят из каталога устройства (`GET /api/ha`). Новая модель
контроллера не требует обновления интеграции.

Репозиторий для установки: [rd1-io/rd1-homeassistant](https://github.com/rd1-io/rd1-homeassistant).

## Установка через HACS

1. HACS → ⋮ → Custom repositories.
2. URL: `https://github.com/rd1-io/rd1-homeassistant`
3. Category: **Integration**.
4. HACS → Integrations → RD1 → Download.
5. Перезапустить Home Assistant.
6. **Settings → Devices & services → Add integration → RD1.**

Устройство в той же сети находится само (mDNS `_rd1._tcp`). Иначе введите
IP контроллера или `rd1-<серийник>.local` (для `RD1S-AABBCC` это
`rd1-aabbcc.local`).

Повторите шаг 6 на каждый физический контроллер.

## Что нужно на контроллере

Прошивка CU с каталогом HA. Проверка:

```bash
curl http://<IP-контроллера>/api/ha
```

В ответе должны быть `"ha_api": 1` и `serial` вида `RD1S-XXXXXX`.
Логин не нужен. CU и Home Assistant — в одной сети.

## Как это устроено

```
CU
  GET  /api/ha      — каталог сущностей
  GET  /api/status  — состояние
  POST /api/cmd     — команды
  mDNS _rd1._tcp    — discovery
```

Опрос каждые 5 с. Команда, которую контроллер отклонил (CO₂-авто, авария),
показывается ошибкой, состояние откатывается.

## Когда обновлять интеграцию

Обычно не нужно: новые датчики и модели приезжают из прошивки.

Обновление HA нужно только для нового типа сущности (`cover`, `valve`, …)
или ломающей версии `ha_api`.

## Диагностика

Карточка интеграции → Download diagnostics: каталог + status
(пароли вырезаны).

## Разработчикам

Исходники в монорепо [rd1-prime-controller](https://github.com/rd1-io/rd1-prime-controller)
(`homeassistant/custom_components/rd1`). Публикация:

```bash
homeassistant/publish.sh          # sync на GitHub
homeassistant/publish.sh v0.1.1   # sync + git tag + GitHub Release
```
