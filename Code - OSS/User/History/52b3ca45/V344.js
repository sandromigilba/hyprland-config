// src/data/materi.js
export const materiReact = [
  {
    id: 1,
    judul: "1. Apa itu React?",
    konten: "React adalah library JavaScript yang dibuat oleh Facebook untuk membangun User Interface (UI) yang interaktif dan dinamis. React menggunakan konsep Component-Based, artinya Anda membuat UI dari potongan-potongan kecil komponen yang bisa digunakan kembali.",
    contoh: "// Contoh komponen sederhana\nfunction Hello() {\n  return <h1>Halo Dunia!</h1>;\n}"
  },
  {
    id: 2,
    judul: "2. Apa itu JSX?",
    konten: "JSX (JavaScript XML) adalah ekstensi sintaksis untuk JavaScript yang tampilannya mirip HTML. JSX mempermudah kita menulis struktur HTML di dalam file JavaScript React.",
    contoh: "const element = <h1 className=\"judul\">Halo dari JSX</h1>;"
  },
  {
    id: 3,
    judul: "3. Komponen & Props",
    konten: "Komponen adalah balok bangunan utama React. Props adalah argumen atau data yang dioper ke dalam komponen agar komponen tersebut bisa menampilkan data yang dinamis.",
    contoh: "function Sambutan(props) {\n  return <h1>Halo, {props.nama}!</h1>;\n}"
  }
];