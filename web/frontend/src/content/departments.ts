// Short fictional descriptions of the departments; a department without one still lists its doctors
export const DEPARTMENT_INFO: Record<string, string> = {
  Dahiliye:
    'Yetişkinlerde iç organ hastalıklarının tanı ve tedavisi; tansiyon, şeker ve kolesterol takibi.',
  Kardiyoloji: 'Kalp ve damar hastalıklarının tanı, tedavi ve takibi.',
  'Göz Hastalıkları': 'Göz muayenesi, görme kusurları ve göz hastalıklarının tedavisi.',
  'Çocuk Sağlığı ve Hastalıkları':
    'Bebek, çocuk ve ergenlerin muayenesi, büyüme ve gelişme takibi.',
  'Kadın Hastalıkları ve Doğum': 'Kadın sağlığı muayeneleri, gebelik takibi ve doğum öncesi bakım.',
  'Ortopedi ve Travmatoloji':
    'Kemik, eklem, kas ve bağ yaralanmaları ile hastalıklarının tedavisi.',
  'Kulak Burun Boğaz': 'Kulak, burun, boğaz ve baş-boyun bölgesi hastalıklarının tedavisi.',
  Nöroloji: 'Beyin, omurilik ve sinir sistemi hastalıklarının tanı ve tedavisi.',
  Dermatoloji: 'Cilt, saç ve tırnak hastalıklarının tanı ve tedavisi.',
}

// Doctors without a department are listed under this name
export const NO_DEPARTMENT = 'Genel'
