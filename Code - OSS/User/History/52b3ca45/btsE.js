// src/data/materi.js

export const materiReact = [
  {
    id: 1,
    judul: "Quick Start",
    konten:
      "React adalah library JavaScript untuk membangun antarmuka pengguna menggunakan komponen yang dapat digunakan kembali. Setiap komponen adalah fungsi JavaScript yang mengembalikan JSX.",
    contoh: `function MyButton() {
  return <button>I'm a button</button>;
}`
  },

  {
    id: 2,
    judul: "Menulis Komponen",
    konten:
      "Komponen adalah blok penyusun utama React. Nama komponen harus diawali huruf kapital dan dapat digunakan seperti tag HTML.",
    contoh: `function Welcome() {
  return <h1>Selamat Datang</h1>;
}

export default function App() {
  return <Welcome />;
}`
  },

  {
    id: 3,
    judul: "JSX",
    konten:
      "JSX memungkinkan Anda menulis markup yang mirip HTML langsung di dalam JavaScript. JSX kemudian diubah menjadi pemanggilan fungsi JavaScript oleh compiler.",
    contoh: `const element = (
  <h1>Hello React!</h1>
);`
  },

  {
    id: 4,
    judul: "Props",
    konten:
      "Props digunakan untuk mengirim data dari parent ke child component sehingga komponen dapat digunakan kembali dengan data yang berbeda.",
    contoh: `function Greeting({ name }) {
  return <h1>Hello {name}</h1>;
}

<Greeting name="Budi" />`
  },

  {
    id: 5,
    judul: "Conditional Rendering",
    konten:
      "React dapat menampilkan UI yang berbeda berdasarkan kondisi menggunakan if, operator &&, atau operator ternary.",
    contoh: `function Login({ isLogin }) {
  return (
    <div>
      {isLogin ? <h1>Dashboard</h1> : <h1>Login</h1>}
    </div>
  );
}`
  },

  {
    id: 6,
    judul: "Rendering List",
    konten:
      "Gunakan method map() untuk merender daftar data. Setiap elemen harus memiliki prop key yang unik.",
    contoh: `const users = ["Andi", "Budi", "Citra"];

<ul>
  {users.map(user => (
    <li key={user}>{user}</li>
  ))}
</ul>`
  },

  {
    id: 7,
    judul: "Event",
    konten:
      "Event pada React ditangani menggunakan event handler seperti onClick, onChange, dan lainnya.",
    contoh: `function Button() {
  function handleClick() {
    alert("Clicked");
  }

  return (
    <button onClick={handleClick}>
      Klik
    </button>
  );
}`
  },

  {
    id: 8,
    judul: "State",
    konten:
      "State adalah data yang dapat berubah. Gunakan hook useState untuk membuat komponen dapat mengingat data dan melakukan render ulang ketika nilainya berubah.",
    contoh: `import { useState } from "react";

function Counter() {
  const [count, setCount] = useState(0);

  return (
    <button onClick={() => setCount(count + 1)}>
      {count}
    </button>
  );
}`
  },

  {
    id: 9,
    judul: "Sharing State",
    konten:
      "Ketika beberapa komponen membutuhkan data yang sama, pindahkan state ke parent component lalu kirimkan melalui props (lifting state up).",
    contoh: `function App() {
  const [value, setValue] = useState("");

  return (
    <>
      <Input value={value} onChange={setValue} />
      <Preview value={value} />
    </>
  );
}`
  },

  {
    id: 10,
    judul: "Effects",
    konten:
      "Gunakan useEffect untuk menjalankan sinkronisasi dengan sistem luar seperti API, timer, atau event browser setelah proses render.",
    contoh: `import { useEffect } from "react";

useEffect(() => {
  document.title = "React";
}, []);`
  }
];