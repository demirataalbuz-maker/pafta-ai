# ai-uretim-38 örnek verisi

`egitim_gunlugu.json`: elle yazılmış, **sentetik** 16 adımlık bir eğitim günlüğü. Gerçek bir eğitimden alınmadı.

İçinde dört sıçrama vardır:

- Adım 4 ve 10: aynı `batch` (`b17`); `lr` ve `grad_norm` olağan.
- Adım 7: `lr` en yüksek değerinde ve `grad_norm` bir önceki adımın üç katından büyük.
- Adım 13: `kayip` `NaN`, `grad_norm` `Infinity`.

Dikkat: `NaN` ve `Infinity` standart JSON'da yoktur. Python'un `json` modülü bunları yazar ve okur, ama başka dillerdeki ayrıştırıcılar bu dosyayı reddedebilir. Gerçek eğitim günlüklerinde de bu yüzden bozuk satırlarla karşılaşılır.

Denemek için: `b17`'lerden birinin adını değiştir (teşhis `veri` olmaktan çıkar mı?) ya da adım 7'nin `grad_norm` değerini 3'e indir.
