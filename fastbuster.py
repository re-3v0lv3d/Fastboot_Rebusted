import curses
import os
import re
import subprocess
from typing import List, Dict, Optional
from tkinter import Tk, filedialog

# Initialize Tkinter for file selection, hiding the main window
root = Tk()
root.withdraw()

# Dictionary of texts for Spanish and English
TEXTS = {
    "es": {
        "select_language": "Seleccione idioma / Select language:",
        "language_option_1": "1. Español",
        "language_option_2": "2. English",
        "select_language_prompt": "Seleccione 1 o 2 y Enter: ",
        "invalid_language": "¡Opción no válida! Presiona Enter para intentarlo otra vez.",
        "connected_devices": "Dispositivos conectados:",
        "select_device_prompt": "Elige un número y pulsa Enter: ",
        "enter_number": "Tienes que poner un número, ¡venga!",
        "no_device_selected": "No seleccionaste ningún dispositivo. Cerrando...",
        "connected_to": "¡Conectado al dispositivo: {serial}!",
        "browsing_partitions": "Explorando particiones en modo Fastboot: {serial}",
        "actions": "Acciones: [q] Salir, [u] Flashear, [o] Borrar, [b] Bootear, [R] Reiniciar, [r] Ir a partición, [Enter] Detalles",
        "go_to_partition": "Escribe el nombre de la partición: {buffer}",
        "flash_confirm": "¿Flashear '{file}' en '{partition}'? (s/n)",
        "flashing": "Flasheando '{file}' en '{partition}'... ¡Espera!",
        "flash_success": "¡'{file}' flasheado en '{partition}' con éxito!",
        "flash_error": "Error al flashear '{partition}': {error}",
        "flash_cancelled": "Flasheo cancelado. No seleccionaste ningún archivo.",
        "wipe_confirm": "¿Borrar '{partition}'? (s/n)",
        "wiping": "Borrando '{partition}'... ¡Espera!",
        "wipe_success": "¡Partición '{partition}' borrada con éxito!",
        "wipe_error": "Error al borrar '{partition}': {error}",
        "boot_file_title": "Seleccionar archivo para bootear",
        "booting": "Booteando '{file}'... ¡Espera!",
        "boot_success": "¡'{file}' booteado con éxito!",
        "boot_error": "Error al bootear '{file}': {error}",
        "rebooting": "Reiniciando dispositivo...",
        "reboot_success": "¡Dispositivo reiniciado!",
        "reboot_error": "Error al reiniciar: {error}",
        "partition_not_found": "Partición '{partition}' no encontrada.",
        "no_partitions": "No se detectaron particiones. Asegúrate de estar en modo Fastboot.",
        "partition_details": "Detalles de '{partition}': {details}"
    },
    "en": {
        "select_language": "Select language / Seleccione idioma:",
        "language_option_1": "1. Spanish",
        "language_option_2": "2. English",
        "select_language_prompt": "Pick 1 or 2 and hit Enter: ",
        "invalid_language": "Invalid choice! Hit Enter to try again.",
        "connected_devices": "Connected devices:",
        "select_device_prompt": "Choose a number and press Enter: ",
        "enter_number": "You gotta enter a number, come on!",
        "no_device_selected": "No device selected. Shutting down...",
        "connected_to": "Connected to device: {serial}!",
        "browsing_partitions": "Browsing partitions in Fastboot mode: {serial}",
        "actions": "Actions: [q] Quit, [u] Flash, [o] Wipe, [b] Boot, [R] Reboot, [r] Go to part., [Enter] Details",
        "go_to_partition": "Enter partition name: {buffer}",
        "flash_confirm": "Flash '{file}' to '{partition}'? (y/n)",
        "flashing": "Flashing '{file}' to '{partition}'...",
        "flash_success": "'{file}' flashed to '{partition}' successfully!",
        "flash_error": "Error flashing '{partition}': {error}",
        "flash_cancelled": "Flash cancelled. You didn't pick a file.",
        "wipe_confirm": "Wipe '{partition}'? (y/n)",
        "wiping": "Wiping '{partition}'...",
        "wipe_success": "Partition '{partition}' wiped successfully!",
        "wipe_error": "Error wiping '{partition}': {error}",
        "boot_file_title": "Select file to boot",
        "booting": "Booting '{file}'...",
        "boot_success": "'{file}' booted successfully!",
        "boot_error": "Error booting '{file}': {error}",
        "rebooting": "Rebooting device...",
        "reboot_success": "Device rebooted!",
        "reboot_error": "Error rebooting: {error}",
        "partition_not_found": "Partition '{partition}' not found.",
        "no_partitions": "No partitions detected. Ensure device is in Fastboot mode.",
        "partition_details": "Details for '{partition}': {details}"
    }
}

def pick_language(screen):
    curses.curs_set(0)
    screen.clear()
    screen.addstr(0, 0, TEXTS['es']['select_language'])
    screen.addstr(1, 0, TEXTS['es']['language_option_1'])
    screen.addstr(2, 0, TEXTS['es']['language_option_2'])
    screen.addstr(4, 0, TEXTS['es']['select_language_prompt'])
    screen.refresh()
    choice = ''
    while True:
        key = screen.getch()
        if key in (ord('1'), ord('2')):
            choice = chr(key)
            screen.addstr(4, len(TEXTS['es']['select_language_prompt']), choice)
            screen.refresh()
        elif key in (curses.KEY_ENTER, 10):
            if choice == '1': return 'es'
            if choice == '2': return 'en'
            screen.addstr(6, 0, TEXTS['es']['invalid_language']); screen.refresh()
        elif key == 27: return 'es'
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            choice = ''; screen.move(4, len(TEXTS['es']['select_language_prompt'])); screen.delch(); screen.refresh()

# Fastboot helper

def run_fastboot(serial: str, args: List[str]) -> subprocess.CompletedProcess:
    cmd = ['fastboot', '-s', serial] + args
    return subprocess.run(cmd, capture_output=True, text=True)

# List partitions
def list_partitions(serial: str) -> List[Dict[str,str]]:
    proc = run_fastboot(serial, ['getvar', 'all'])
    items=[]
    for line in (proc.stdout+proc.stderr).splitlines():
        m = re.match(r"\(bootloader\) partition-(.+?):(.+)", line)
        if m:
            items.append({'name':m.group(1).strip(), 'details':m.group(2).strip()})
    return sorted(items, key=lambda x: x['name'])

# Actions: flash, wipe, boot, reboot
def apply_flash(screen, serial, partition, file_path, max_y, lang):
    screen.addstr(max_y-3,0, TEXTS[lang]['flashing'].format(file=os.path.basename(file_path), partition=partition)); screen.refresh()
    res = run_fastboot(serial, ['flash', partition, file_path])
    msg = TEXTS[lang]['flash_success'] if res.returncode==0 else TEXTS[lang]['flash_error'].format(partition=partition, error=res.stderr.strip())
    screen.addstr(max_y-3,0,msg); screen.clrtoeol(); screen.refresh(); screen.getch()


def apply_wipe(screen, serial, partition, max_y, lang):
    screen.addstr(max_y-3,0, TEXTS[lang]['wiping'].format(partition=partition)); screen.refresh()
    res=run_fastboot(serial,['erase',partition])
    msg = TEXTS[lang]['wipe_success'] if res.returncode==0 else TEXTS[lang]['wipe_error'].format(partition=partition, error=res.stderr.strip())
    screen.addstr(max_y-3,0,msg); screen.clrtoeol(); screen.refresh(); screen.getch()


def apply_boot(screen, serial, file_path, max_y, lang):
    screen.addstr(max_y-3,0,TEXTS[lang]['booting'].format(file=os.path.basename(file_path))); screen.refresh()
    res=run_fastboot(serial,['boot',file_path])
    msg = TEXTS[lang]['boot_success'].format(file=os.path.basename(file_path)) if res.returncode==0 else TEXTS[lang]['boot_error'].format(file=os.path.basename(file_path),error=res.stderr.strip())
    screen.addstr(max_y-3,0,msg); screen.clrtoeol(); screen.refresh(); screen.getch()


def apply_reboot(screen, serial, max_y, lang):
    screen.addstr(max_y-3,0,TEXTS[lang]['rebooting']); screen.refresh()
    res=run_fastboot(serial,['reboot'])
    msg = TEXTS[lang]['reboot_success'] if res.returncode==0 else TEXTS[lang]['reboot_error'].format(error=res.stderr.strip())
    screen.addstr(max_y-3,0,msg); screen.clrtoeol(); screen.refresh(); screen.getch()

# Main partition explorer

def partition_explorer(screen, serial: str, language: str):
    items = list_partitions(serial)
    if not items:
        screen.addstr(0,0,TEXTS[language]['no_partitions'],curses.A_DIM); screen.getch(); return
    cursor, top = 0,0
    max_y,max_x = screen.getmaxyx()
    entering=False; buffer=''
    selected_file=''

    def draw():
        screen.clear()
        screen.addstr(0,0,TEXTS[language]['browsing_partitions'].format(serial=serial),curses.A_BOLD)
        for i in range(top, min(top+max_y-4, len(items))):
            attr = curses.A_REVERSE if i==cursor else curses.A_NORMAL
            itm=items[i]
            screen.addstr(i-top+2,0,f"[PART] {itm['name']}: {itm['details']}",attr)
        screen.addstr(max_y-2,0,TEXTS[language]['actions'],curses.A_DIM)
        if entering:
            screen.addstr(max_y-1,0,TEXTS[language]['go_to_partition'].format(buffer=buffer)); screen.clrtoeol()
        screen.refresh()

    draw()
    while True:
        k=screen.getch()
        if entering:
            if k in (10, curses.KEY_ENTER):
                name=buffer.strip(); entering=False; buffer=''
                for idx,it in enumerate(items):
                    if it['name'].lower()==name.lower(): cursor, top = idx, max(0, idx-(max_y-4)//2); break
                else:
                    screen.addstr(max_y-3,0,TEXTS[language]['partition_not_found'].format(partition=name)); screen.getch()
            elif k==27: entering=False; buffer=''
            elif k in (curses.KEY_BACKSPACE,127,8): buffer=buffer[:-1]
            elif 32<=k<=126: buffer+=chr(k)
            draw(); continue

        if k==curses.KEY_DOWN:
            cursor=min(cursor+1,len(items)-1);
            if cursor>=top+max_y-4: top+=1
        elif k==curses.KEY_UP:
            cursor=max(cursor-1,0);
            if cursor<top: top-=1
        elif k in (10, curses.KEY_ENTER, 13):
            it=items[cursor]; screen.addstr(max_y-3,0,TEXTS[language]['partition_details'].format(partition=it['name'],details=it['details'])); screen.getch()
        elif k==ord('u'):
            f=filedialog.askopenfilename(filetypes=[("Image Files","*.img"),("All","*.*")],title="Select file to flash" if language=='en' else "Seleccionar archivo para flashear")
            if f: selected_file=f; screen.clear(); screen.addstr(max_y-3,0,TEXTS[language]['flash_confirm'].format(file=os.path.basename(f),partition=items[cursor]['name'])); screen.refresh();
            # confirm
            c=screen.getch();
            if c== (ord('y') if language=='en' else ord('s')): apply_flash(screen, serial, items[cursor]['name'], selected_file, max_y, language)
        elif k==ord('o'):
            screen.clear(); screen.addstr(max_y-3,0,TEXTS[language]['wipe_confirm'].format(partition=items[cursor]['name'])); screen.refresh();
            c=screen.getch();
            if c== (ord('y') if language=='en' else ord('s')): apply_wipe(screen, serial, items[cursor]['name'], max_y, language)
        elif k==ord('b'):
            f=filedialog.askopenfilename(title=TEXTS[language]['boot_file_title'], filetypes=[("Image Files","*.img"),("All","*.*")])
            if f: apply_boot(screen, serial, f, max_y, language)
        elif k==ord('R'):
            apply_reboot(screen, serial, max_y, language)
        elif k==ord('r'):
            entering=True; buffer=''
        elif k==ord('q'):
            break
        draw()

# Entry point
def main(screen):
    curses.curs_set(0)
    lang = pick_language(screen)
    serials = subprocess.run(["fastboot","devices"],capture_output=True,text=True).stdout.strip().splitlines()
    if not serials:
        screen.clear(); screen.addstr(0,0,TEXTS[lang]['no_device_selected'],curses.A_BOLD); screen.refresh(); curses.napms(1500); return
    serial=serials[0].split()[0]
    screen.clear(); screen.addstr(0,0,TEXTS[lang]['connected_to'].format(serial=serial),curses.A_BOLD); screen.refresh(); curses.napms(1000)
    partition_explorer(screen, serial, lang)

if __name__=='__main__':
    try: curses.wrapper(main)
    except Exception as e:
        curses.endwin(); print(f"Error: {e}")
