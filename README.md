## И о погоде

В современном мире люди часто перемещаются в новые места, и не всегда понятно, на какой климат там можно рассчитывать. Сделай систему, которая поможет в такой ситуации. 

По указанному городу или месту найди данные о климате (типичная температура, осадки, ветер) и непосредственно прогноз погоды на ближайшие дни – и совмести это для вывода пользователю. И климат, и прогноз лучше брать из нескольких источников (потому что каждый источник более точен только для определенных мест Земли).

Сохраняй данные в локальную базу для кеширования, чтобы снизить нагрузку на внешние сервисы и ускорить ответ, а также иметь возможность последующего анализа. В качестве интерфейса можно оставить простой REST API, а можно сделать веб-приложение или телеграм-бот. В идеале можно сделать разные варианты интерфейса, поэтому продумай такое API, которое универсально подойдет для разных применений.