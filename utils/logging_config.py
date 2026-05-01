import logging

def obtener_logger(nombre):

    logger = logging.getLogger(nombre)
    logger .setLevel(logging.INFO)

    if not logger.handlers:
        formato = logging.Formatter('%(message)s')

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formato)
        logger.addHandler(console_handler)
    
    return logger

# Función especial para ver el "dibujo" de la matriz en el log
def log_matriz(logger, matriz):
    logger.info("\n" + "="*20)
    for fila in matriz:
        # Convierte [1, 0] en "[ DIRTY ][ CLEAN ]"
        visual = "".join(["[ 💩 ]" if celda == 1 else "[ ✨ ]" for celda in fila])
        logger.info(visual)
    logger.info("="*20 + "\n")