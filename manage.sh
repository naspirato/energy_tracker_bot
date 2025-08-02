#!/bin/bash

# Простой скрипт управления Telegram ботом
# Использование: ./manage.sh [start|stop|restart|status|logs]

BOT_SCRIPT="bot.py"
LOG_FILE="bot.log"
PID_FILE="bot.pid"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для проверки, запущен ли бот
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    return 1
}

# Функция для запуска бота
start_bot() {
    echo -e "${YELLOW}🚀 Запуск бота...${NC}"
    
    if is_running; then
        echo -e "${RED}❌ Бот уже запущен!${NC}"
        return 1
    fi
    
    # Проверяем виртуальное окружение
    if [ ! -d "venv" ]; then
        echo -e "${RED}❌ Виртуальное окружение не найдено!${NC}"
        echo "💡 Создайте виртуальное окружение: python -m venv venv"
        return 1
    fi
    
    # Запускаем бота в фоне
    source venv/bin/activate && python "$BOT_SCRIPT" > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"
    
    echo -e "${GREEN}✅ Бот запущен (PID: $pid)${NC}"
    echo "📝 Логи: $LOG_FILE"
}

# Функция для остановки бота
stop_bot() {
    echo -e "${YELLOW}🛑 Остановка бота...${NC}"
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid"
            echo -e "${GREEN}✅ Бот остановлен${NC}"
        else
            echo -e "${YELLOW}⚠️  Процесс не найден${NC}"
        fi
        rm -f "$PID_FILE"
    else
        echo -e "${YELLOW}⚠️  PID файл не найден${NC}"
    fi
    
    # Убиваем все процессы python bot.py на всякий случай
    pkill -f "python.*$BOT_SCRIPT" 2>/dev/null || true
}

# Функция для перезапуска бота
restart_bot() {
    echo -e "${YELLOW}🔄 Перезапуск бота...${NC}"
    stop_bot
    sleep 2
    start_bot
}

# Функция для показа статуса
show_status() {
    echo -e "${YELLOW}📊 Статус бота:${NC}"
    
    if is_running; then
        local pid=$(cat "$PID_FILE")
        echo -e "${GREEN}✅ Бот запущен (PID: $pid)${NC}"
        
        # Показываем последние логи
        if [ -f "$LOG_FILE" ]; then
            echo -e "\n📝 Последние логи:"
            tail -5 "$LOG_FILE"
        fi
    else
        echo -e "${RED}❌ Бот не запущен${NC}"
    fi
}

# Функция для показа логов
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}📝 Показ логов (Ctrl+C для выхода):${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${RED}❌ Файл логов не найден${NC}"
    fi
}

# Основная логика
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Команды:"
        echo "  start   - Запустить бота"
        echo "  stop    - Остановить бота"
        echo "  restart - Перезапустить бота"
        echo "  status  - Показать статус"
        echo "  logs    - Показать логи в реальном времени"
        exit 1
        ;;
esac 