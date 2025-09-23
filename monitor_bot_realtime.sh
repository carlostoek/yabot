#!/bin/bash
# Monitor en tiempo real del bot para ver qué pasa durante el shutdown
# Uso: ./monitor_bot_realtime.sh <PID>

if [ -z "$1" ]; then
    echo "Uso: $0 <PID_del_bot>"
    echo "Este script monitoreará el proceso en tiempo real"
    echo "Presiona Ctrl+C para parar el monitoreo"
    exit 1
fi

PID=$1
LOG_FILE="realtime_monitor_$(date +%Y%m%d_%H%M%S).log"

echo "=== MONITOR EN TIEMPO REAL - PID: $PID ===" | tee $LOG_FILE
echo "Presiona Ctrl+C para detener el monitoreo" | tee -a $LOG_FILE
echo "Log: $LOG_FILE" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# Función para capturar señales y terminar elegantemente
cleanup() {
    echo "" | tee -a $LOG_FILE
    echo "=== MONITOREO TERMINADO ===" | tee -a $LOG_FILE
    echo "Log guardado en: $LOG_FILE" | tee -a $LOG_FILE
    exit 0
}

trap cleanup SIGINT SIGTERM

# Monitoreo continuo
while true; do
    # Verificar si el proceso aún existe
    if ! kill -0 $PID 2>/dev/null; then
        echo "$(date): PROCESO $PID YA NO EXISTE - SE CERRÓ CORRECTAMENTE" | tee -a $LOG_FILE
        break
    fi

    echo "=== $(date) ===" | tee -a $LOG_FILE

    # Estado básico del proceso
    echo "Estado del proceso:" | tee -a $LOG_FILE
    ps -p $PID -o pid,stat,pcpu,pmem,time,command | grep -v PID | tee -a $LOG_FILE

    # Número de hilos
    THREADS=$(ps -L -p $PID --no-headers 2>/dev/null | wc -l)
    echo "Número de hilos activos: $THREADS" | tee -a $LOG_FILE

    # Conexiones de red
    NET_CONNECTIONS=$(lsof -i -p $PID 2>/dev/null | wc -l)
    if [ $NET_CONNECTIONS -gt 1 ]; then
        echo "Conexiones de red abiertas: $((NET_CONNECTIONS - 1))" | tee -a $LOG_FILE
        lsof -i -p $PID 2>/dev/null | grep -v COMMAND | tee -a $LOG_FILE
    else
        echo "Sin conexiones de red activas" | tee -a $LOG_FILE
    fi

    # Archivos abiertos (solo contar)
    OPEN_FILES=$(lsof -p $PID 2>/dev/null | wc -l)
    echo "Descriptores de archivo abiertos: $((OPEN_FILES - 1))" | tee -a $LOG_FILE

    echo "---" | tee -a $LOG_FILE
    sleep 2
done

cleanup