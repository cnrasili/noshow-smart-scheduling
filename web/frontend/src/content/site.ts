// Static content of the fictional hospital site; every address, number and text is made up
import { INSTITUTION_NAME } from '../config'

export const DISCLAIMER =
  'Bu site bir ders projesidir; gerçek bir hastaneye ait değildir. Hekim ve hasta bilgileri kurgusaldır.'

export const CONTACT = {
  address: 'Şifa Mahallesi, Sağlık Caddesi No: 1, Merkez',
  phone: '0 (000) 000 00 00',
  email: 'iletisim@sehirhastanesi.example',
  appointmentEmail: 'randevu@sehirhastanesi.example',
  hours: [
    ['Poliklinikler', 'Hafta içi 08:00–17:00'],
    ['Acil servis', '7 gün 24 saat'],
    ['Hasta kabul', 'Hafta içi 07:30–17:00'],
  ],
  transport: [
    ['Otobüs', 'Hastane durağında inen hatlar ana girişe 2 dakika yürüme mesafesindedir.'],
    ['Raylı sistem', 'Sağlık durağından ücretsiz servis aracı her 15 dakikada bir kalkar.'],
    ['Özel araç', 'Ana giriş ve poliklinik girişinde ziyaretçi otoparkı bulunur.'],
  ],
} as const

export interface Announcement {
  slug: string
  // Day key, YYYY-MM-DD
  date: string
  title: string
  summary: string
  body: string[]
}

// Newest first
export const ANNOUNCEMENTS: Announcement[] = [
  {
    slug: 'online-randevu-yenilendi',
    date: '2026-10-06',
    title: 'Online Randevu sistemimiz yenilendi',
    summary: 'Randevularınızı artık branş, hekim, gün ve saat seçerek birkaç adımda alabilirsiniz.',
    body: [
      'Online Randevu sistemimiz yenilendi. Hasta girişi yaptıktan sonra önce branşı, sonra hekimi, ardından uygun gün ve saati seçerek randevunuzu alabilirsiniz.',
      'Randevunuz alındığında kayıtlı e-posta adresinize bir onay e-postası gönderilir. Randevularınızı "Randevularım" sayfasından görebilir, gelemeyecekseniz iptal edebilirsiniz.',
    ],
  },
  {
    slug: 'randevu-iptali-hatirlatmasi',
    date: '2026-09-28',
    title: 'Gelemeyeceğiniz randevuları iptal etmeyi unutmayın',
    summary: 'İptal edilen her randevu, başka bir hastanın daha erken muayene olmasını sağlar.',
    body: [
      'Randevusuna gelmeyen hastalar nedeniyle her gün çok sayıda muayene saati boş kalmaktadır. Randevunuza gelemeyecekseniz lütfen en kısa sürede iptal edin.',
      'İptal işlemini Online Randevu üzerinden, hasta girişi yaptıktan sonra "Randevularım" sayfasından yapabilirsiniz.',
    ],
  },
  {
    slug: 'poliklinik-girisi-duzenlemesi',
    date: '2026-09-15',
    title: 'Poliklinik girişinde yeni yönlendirme düzeni',
    summary: 'Poliklinik girişindeki danışma bankoları ve yönlendirme tabelaları yenilendi.',
    body: [
      'Poliklinik girişindeki danışma bankoları yeniden düzenlendi. Randevunuz varsa doğrudan ilgili polikliniğin bekleme alanına geçebilirsiniz.',
      'Yardıma ihtiyaç duyduğunuzda danışma görevlilerimize başvurabilirsiniz.',
    ],
  },
  {
    slug: 'ziyaretci-otoparki',
    date: '2026-09-02',
    title: 'Ziyaretçi otoparkı kapasitesi artırıldı',
    summary: 'Poliklinik girişindeki ziyaretçi otoparkına yeni park alanları eklendi.',
    body: [
      'Poliklinik girişindeki ziyaretçi otoparkına yeni park alanları eklendi. Engelli park alanları ana girişe en yakın bölümde yer almaktadır.',
    ],
  },
]

export const ABOUT = {
  intro: `${INSTITUTION_NAME}, birçok branşta poliklinik hizmeti veren kurgusal bir şehir hastanesidir. Hastalarımız randevularını Online Randevu üzerinden alır; hekimlerimiz günlük hasta listelerini aynı sistemden yönetir.`,
  sections: [
    {
      title: 'Misyonumuz',
      text: 'Hastalarımıza zamanında, güvenli ve erişilebilir sağlık hizmeti sunmak; randevu saatlerini verimli kullanarak bekleme sürelerini kısaltmak.',
    },
    {
      title: 'Vizyonumuz',
      text: 'Randevu planlamasında veriye dayalı yöntemler kullanan, hasta memnuniyeti yüksek bir şehir hastanesi olmak.',
    },
    {
      title: 'Değerlerimiz',
      text: 'Hasta odaklılık, mahremiyete saygı, şeffaflık ve ekip çalışması.',
    },
  ],
}

export const GUIDE = [
  {
    id: 'randevu',
    title: 'Randevu nasıl alınır?',
    steps: [
      'Sayfanın üst kısmındaki "Online Randevu" bağlantısını seçin.',
      'T.C. kimlik numaranız ve şifrenizle hasta girişi yapın.',
      'Branşı ve hekimi seçin.',
      'Uygun günü ve saati seçip randevuyu onaylayın.',
      'Randevu numaranızı not alın; randevularınızı "Randevularım" sayfasından izleyin.',
    ],
  },
  {
    id: 'yaninizda',
    title: 'Randevuya gelirken yanınızda bulundurun',
    steps: [
      'Kimlik belgeniz.',
      'Varsa önceki tetkik sonuçlarınız ve kullandığınız ilaçların listesi.',
      'Randevu numaranız.',
    ],
  },
  {
    id: 'erken-gelin',
    title: 'Randevu saatinden 15 dakika önce gelin',
    steps: [
      'Hasta kabul ve yönlendirme işlemleri için randevu saatinizden 15 dakika önce hastanede olun.',
      'Geç kalırsanız muayeneniz bir sonraki uygun saate kayabilir.',
    ],
  },
  {
    id: 'iptal',
    title: 'Gelemeyecekseniz randevunuzu iptal edin',
    steps: [
      'Hasta girişi yapıp "Randevularım" sayfasından randevunuzu iptal edin.',
      'Boşalan saat başka bir hastaya verilir; böylece bekleme süreleri kısalır.',
    ],
  },
]
