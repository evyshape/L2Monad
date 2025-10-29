package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/registry"
)

import "syscall"
import "unsafe"

var kernel32 = syscall.NewLazyDLL("kernel32.dll")
var procSetConsoleTitle = kernel32.NewProc("SetConsoleTitleW")

func title(t string) {
	u := syscall.StringToUTF16Ptr(t)
	procSetConsoleTitle.Call(uintptr(unsafe.Pointer(u)))
}

func admin() bool {
	var sid *windows.SID
	err := windows.AllocateAndInitializeSid(
		&windows.SECURITY_NT_AUTHORITY, 2,
		windows.SECURITY_BUILTIN_DOMAIN_RID, windows.DOMAIN_ALIAS_RID_ADMINS,
		0, 0, 0, 0, 0, 0, &sid)
	if err != nil {
		return false
	}
	defer windows.FreeSid(sid)
	t := windows.Token(0)
	member, _ := t.IsMember(sid)
	return member
}

func fsize(b int64) string {
	u := int64(1024)
	if b < u {
		return fmt.Sprintf("%d B", b)
	}
	div, exp := u, 0
	for n := b / u; n >= u; n /= u {
		div *= u
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(b)/float64(div), "KMGTPE"[exp])
}

func dl(url, dst string) error {
	fmt.Println("Скачиваю...")

	if _, err := os.Stat(dst); err == nil {
		if err := os.Remove(dst); err != nil {
			return fmt.Errorf("не смог удалить файл: %v", err)
		}
	}

	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	total := resp.ContentLength
	got := int64(0)
	buf := make([]byte, 32*1024)

	for {
		n, err := resp.Body.Read(buf)
		if n > 0 {
			out.Write(buf[:n])
			got += int64(n)
		}
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}
	}

	fmt.Printf("Скачал: %s\n", fsize(total))
	return nil
}

func pyPath() string {
	paths := []string{
		filepath.Join(os.Getenv("ProgramFiles"), "Python311", "python.exe"),
		filepath.Join(os.Getenv("LOCALAPPDATA"), "Programs", "Python", "Python311", "python.exe"),
		"python.exe",
	}
	for _, p := range paths {
		if _, err := exec.LookPath(p); err == nil {
			return p
		}
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ""
}

func pyVer() string {
	p := pyPath()
	if p == "" {
		return ""
	}
	out, err := exec.Command(p, "--version").Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}

func updPath() error {
	k, err := registry.OpenKey(registry.LOCAL_MACHINE,
		`SYSTEM\CurrentControlSet\Control\Session Manager\Environment`,
		registry.QUERY_VALUE)
	if err != nil {
		return err
	}
	defer k.Close()

	path, _, err := k.GetStringValue("Path")
	if err != nil {
		return err
	}

	uk, err := registry.OpenKey(registry.CURRENT_USER, `Environment`, registry.QUERY_VALUE)
	if err == nil {
		defer uk.Close()
		up, _, err := uk.GetStringValue("Path")
		if err == nil {
			path += ";" + up
		}
	}

	return os.Setenv("PATH", path)
}

func instPy() error {
	fmt.Println("\n[1/3] Проверка")
	v := pyVer()
	if v != "" {
		fmt.Println("Питон найден:", v)
		return nil
	}

	fmt.Println("Питон не найден, устанавливаю...")
	title("Скачивание питончика...")
	url := "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe"
	tmp := filepath.Join(os.TempDir(), "python-3.11.5.exe")

	if err := dl(url, tmp); err != nil {
		return fmt.Errorf("не удалось скачать петухона: %v", err)
	}

	fmt.Println("Устанавливаю...")
	cmd := exec.Command(tmp, "/quiet", "InstallAllUsers=1", "PrependPath=1")
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("не удалось установить Python: %v", err)
	}

	time.Sleep(2 * time.Second)
	updPath()

	v = pyVer()
	if v == "" {
		return fmt.Errorf("шото пошло не так")
	}
	fmt.Println("Питон установлен:", v)
	title("Питон установлен")

	return nil
}

func instInt() error {
	fmt.Println("\n[2/3] Проверка интерсепшна")
	kbd := filepath.Join(os.Getenv("windir"), "System32", "drivers", "keyboard.sys")
	ms := filepath.Join(os.Getenv("windir"), "System32", "drivers", "mouse.sys")

	if _, err := os.Stat(kbd); err == nil {
		if _, err := os.Stat(ms); err == nil {
			fmt.Println("Драйвер уже установлен")
			return nil
		}
	}

	fmt.Println("Устанавливаю драйвер...")
	exePath, _ := filepath.Abs("install-interception.exe")
	cmd := exec.Command(exePath, "/install")

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("не удалось установить драйвер: %v", err)
	}

	fmt.Println("Драйвер установлен")
	title("Установка драйвера")
	return nil
}

func instDeps() error {
	fmt.Println("\n[3/3] Установка зависимостей...")
	title("Установка зависимостей")
	req := filepath.Join("..", "requirements.txt")
	if _, err := os.Stat(req); os.IsNotExist(err) {
		fmt.Println("requirements.txt не найден, пропускаю")
		return nil
	}

	updPath()
	p := pyPath()
	if p == "" {
		return fmt.Errorf("Питон не найден")
	}

	fmt.Println("Обновляю пакетник")
	exec.Command(p, "-m", "pip", "install", "--upgrade", "pip", "--quiet").Run()

	fmt.Println("Устанавливаю пакеты")
	cmd := exec.Command(p, "-m", "pip", "install", "-r", req)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	err := cmd.Run()
	if err != nil {
		return fmt.Errorf("не удалось установить зависимости: %v", err)
	}

	fmt.Println("Успешно установил все пакеты")
	return nil
}

func main() {
	fmt.Println(strings.Repeat("=", 50))
	fmt.Println("  L2Monad (tg: @BotLineage2M)")
	fmt.Println(strings.Repeat("=", 50))

	if !admin() {
		fmt.Println("Нужны права админа! Запусти инсталлер от админки!")
		fmt.Scanln()
		os.Exit(1)
	}

	fmt.Println("Начинаем установку...")

	start := time.Now()

	if err := instPy(); err != nil {
		fmt.Println("Ошибка:", err)
		fmt.Scanln()
		os.Exit(1)
	}

	if err := instInt(); err != nil {
		fmt.Println("Ошибка:", err)
		fmt.Scanln()
		os.Exit(1)
	}

	if err := instDeps(); err != nil {
		fmt.Println("Ошибка:", err)
		fmt.Scanln()
		os.Exit(1)
	}

	fmt.Println(strings.Repeat("=", 50))
	fmt.Println("Установка завершена!")
	title("Установка завершена!")
	fmt.Println(strings.Repeat("=", 50))
	fmt.Printf("Время установки: %.1f секунд\n", time.Since(start).Seconds())
	fmt.Println("Перезагрузи компьютер если перед установкой не было драйвера.")
	fmt.Scanln()
}
