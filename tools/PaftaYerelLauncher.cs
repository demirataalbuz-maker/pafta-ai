// Pafta.exe — bu bilgisayar için yerel başlatıcı.
// Hiçbir şey indirmez, kurmaz, git çalıştırmaz. Exe'nin yanındaki Pafta.pyw'yi açar ve AI derslerinin
// gerçek deney adımları için proje içindeki .ai-venv ortamını gösterir.
// Derleme: csc.exe /nologo /target:winexe /optimize+ /r:System.Windows.Forms.dll /win32icon:icon.ico /out:Pafta.exe tools\PaftaYerelLauncher.cs
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace PaftaYerel
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            string root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\', '/');
            string pyw = Path.Combine(root, "Pafta.pyw");
            if (!File.Exists(pyw))
            {
                Hata("Pafta.pyw bulunamadı. Pafta.exe proje klasörünün içinde durmalı:\n" + root);
                return;
            }

            string python = PythonBul();
            if (python == null)
            {
                Hata("Python 3.11 ya da üstü bulunamadı (pythonw.exe).\nPython'u python.org'dan kurup yeniden deneyin.");
                return;
            }

            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = python,
                Arguments = "\"" + pyw + "\"",
                WorkingDirectory = root,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            psi.EnvironmentVariables["PYTHONUTF8"] = "1";

            // Ayrı uygulama (örneğin yalnız AI dersleri): kendi veri klasörünü kullanır, tam Pafta'nın
            // ilerlemesine ve açık penceresine karışmaz. pafta-veri.txt içinde %LOCALAPPDATA% altındaki klasör adı yazar.
            string veriAyari = Path.Combine(root, "pafta-veri.txt");
            if (File.Exists(veriAyari) && string.IsNullOrEmpty(Environment.GetEnvironmentVariable("PAFTA_DATA")))
            {
                string ad = File.ReadAllText(veriAyari).Trim();
                if (ad.Length > 0 && ad.IndexOfAny(Path.GetInvalidFileNameChars()) < 0)
                    psi.EnvironmentVariables["PAFTA_DATA"] = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), ad);
            }

            // AI dersleri: model ve torch ortamı (proje içindeki .ai-venv, CUDA destekli)
            string aiPython = Path.Combine(root, ".ai-venv", "Scripts", "python.exe");
            if (File.Exists(aiPython) && string.IsNullOrEmpty(Environment.GetEnvironmentVariable("PAFTA_AI_PYTHON")))
                psi.EnvironmentVariables["PAFTA_AI_PYTHON"] = aiPython;

            // ai-savunma-38: bu kopyadaki OCR kurulum kaydı makinedeki imajla eşleşmiyor; eşleşen kayıt kardeş kopyada.
            string ocrKayit = Path.Combine(Path.GetDirectoryName(root) ?? root, "Pafta-AI-GercekLab", "outputs", "ocr38-kurulum", "kurulum.json");
            if (File.Exists(ocrKayit) && string.IsNullOrEmpty(Environment.GetEnvironmentVariable("PAFTA_OCR38_INSTALL")))
                psi.EnvironmentVariables["PAFTA_OCR38_INSTALL"] = ocrKayit;

            try
            {
                Process.Start(psi);
            }
            catch (Exception e)
            {
                Hata("Pafta başlatılamadı:\n" + e.Message);
            }
        }

        static string PythonBul()
        {
            string programs = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python");
            string[] koklar = { programs, Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles) };
            foreach (string kok in koklar)
            {
                if (!Directory.Exists(kok)) continue;
                string[] dizinler = Directory.GetDirectories(kok, "Python3*");
                Array.Sort(dizinler);
                Array.Reverse(dizinler); // en yeni sürüm önce
                foreach (string d in dizinler)
                {
                    string ad = Path.GetFileName(d);
                    int surum;
                    if (ad.Length >= 8 && int.TryParse(ad.Substring(7).Split('-')[0], out surum) && surum < 11) continue;
                    string p = Path.Combine(d, "pythonw.exe");
                    if (File.Exists(p)) return p;
                }
            }
            return null;
        }

        static void Hata(string mesaj)
        {
            MessageBox.Show(mesaj, "Pafta", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
