#!/bin/bash
# Script de diagnóstico automático para bot que no se cierra
# Uso: ./diagnostic_bot.sh <PID>

if [ -z "$1" ]; then
    echo "Uso: $0 <PID_del_bot>"
    echo "Primero ejecuta el bot y luego obtén el PID con: ps aux | grep python"
    exit 1
fi

PID=$1
LOG_FILE="bot_diagnostic_$(date +%Y%m%d_%H%M%S).log"

echo "=== DIAGNÓSTICO DEL BOT - PID: $PID ===" | tee $LOG_FILE
echo "Timestamp: $(date)" | tee -a $LOG_FILE
echo "Log guardado en: $LOG_FILE" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# Verificar que el proceso existe
if ! kill -0 $PID 2>/dev/null; then
    echo "ERROR: El proceso $PID no existe o no tenemos permisos" | tee -a $LOG_FILE
    exit 1
fi

echo "1. === INFORMACIÓN DEL PROCESO PRINCIPAL ===" | tee -a $LOG_FILE
ps -p $PID -o pid,ppid,pgid,sid,tty,stat,time,command | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

echo "2. === PROCESOS HIJOS ===" | tee -a $LOG_FILE
echo "Buscando procesos hijos del PID $PID:" | tee -a $LOG_FILE
ps --ppid $PID -o pid,ppid,pgid,sid,tty,stat,time,command 2>/dev/null | tee -a $LOG_FILE
if [ $? -ne 0 ]; then
    echo "No se encontraron procesos hijos" | tee -a $LOG_FILE
fi
echo "" | tee -a $LOG_FILE

echo "3. === ÁRBOL DE PROCESOS ===" | tee -a $LOG_FILE
echo "Árbol completo desde el proceso:" | tee -a $LOG_FILE
pstree -p $PID 2>/dev/null | tee -a $LOG_FILE
if [ $? -ne 0 ]; then
    echo "pstree no disponible o error" | tee -a $LOG_FILE
fi
echo "" | tee -a $LOG_FILE

echo "4. === HILOS (THREADS) ===" | tee -a $LOG_FILE
echo "Hilos del proceso principal:" | tee -a $LOG_FILE
ps -L -p $PID -o pid,lwp,nlwp,psr,pcpu,pmem,stat,time,comm 2>/dev/null | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

echo "5. === ARCHIVOS ABIERTOS (TOP 20) ===" | tee -a $LOG_FILE
echo "Archivos y descriptores abiertos:" | tee -a $LOG_FILE
lsof -p $PID 2>/dev/null | head -20 | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

echo "6. === CONEXIONES DE RED ===" | tee -a $LOG_FILE
echo "Conexiones de red activas:" | tee -a $LOG_FILE
lsof -i -p $PID 2>/dev/null | tee -a $LOG_FILE
if [ $? -ne 0 ]; then
    echo "No se encontraron conexiones de red o lsof no disponible" | tee -a $LOG_FILE
fi
echo "" | tee -a $LOG_FILE

echo "7. === SOCKETS Y CONEXIONES (NETSTAT) ===" | tee -a $LOG_FILE
echo "Verificando con netstat:" | tee -a $LOG_FILE
netstat -tulpn 2>/dev/null | grep $PID | tee -a $LOG_FILE
ss -tulpn 2>/dev/null | grep $PID | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

echo "8. === ESTADO DE MEMORIA ===" | tee -a $LOG_FILE
echo "Uso de memoria del proceso:" | tee -a $LOG_FILE
ps -p $PID -o pid,vsz,rss,pmem,command | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

if [ -f "/proc/$PID/status" ]; then
    echo "9. === INFORMACIÓN DETALLADA DEL PROCESO ===" | tee -a $LOG_FILE
    echo "Estado desde /proc/$PID/status:" | tee -a $LOG_FILE
    grep -E "(State|Threads|VmSize|VmRSS)" /proc/$PID/status | tee -a $LOG_FILE
    echo "" | tee -a $LOG_FILE
fi

echo "10. === SEÑALES PENDIENTES ===" | tee -a $LOG_FILE
if [ -f "/proc/$PID/status" ]; then
    echo "Señales pendientes y bloqueadas:" | tee -a $LOG_FILE
    grep -E "(SigPnd|SigBlk|SigIgn|SigCgt)" /proc/$PID/status | tee -a $LOG_FILE
else
    echo "/proc/$PID/status no disponible" | tee -a $LOG_FILE
fi
echo "" | tee -a $LOG_FILE

echo "=== DIAGNÓSTICO COMPLETADO ===" | tee -a $LOG_FILE
echo "Para ver el archivo completo: cat $LOG_FILE" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "RECOMENDACIONES:" | tee -a $LOG_FILE
echo "1. Si hay muchos hilos activos, revisar tareas async que no se cancelan" | tee -a $LOG_FILE
echo "2. Si hay conexiones de red abiertas, verificar cierre de sockets" | tee -a $LOG_FILE
echo "3. Si el estado es 'S' (sleeping), el proceso está esperando algo" | tee -a $LOG_FILE
echo "4. Si el estado es 'D' (uninterruptible sleep), hay problema de I/O" | tee -a $LOG_FILE