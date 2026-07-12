import { useState } from 'react';
import { materiReact } from './data/materi';
import './App.css';

function App() {
  // State untuk menyimpan materi yang sedang aktif dipilih user
  const [materiAktif, setMateriAktif] = useState(materiReact[0]);

  return (
    <div className="app-container">
      {/* Header Web */}
      <header className="navbar">
        <h2>🚀 KelasCoding: Belajar React v19</h2>
      </header>

      <div className="main-content">
        {/* Sidebar Navigasi Materi */}
        <aside className="sidebar">
          <h3>Materi 1: Dasar React</h3>
          <ul>
            {materiReact.map((materi) => (
              <li key={materi.id}>
                <button 
                  className={materiAktif.id === materi.id ? 'active' : ''}
                  onClick={() => setMateriAktif(materi)}
                >
                  {materi.judul}
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* Konten Materi */}
        <main className="content-area">
          <h1>{materiAktif.judul}</h1>
          <p className="penjelasan">{materiAktif.konten}</p>
          
          {/* Box Contoh Kode */}
          <div className="code-box">
            <h4>Contoh Potongan Kode:</h4>
            <pre>
              <code>{materiAktif.contoh}</code>
            </pre>
          </div>

          {/* Tombol Navigasi Bawah */}
          <div className="navigation-buttons">
            <button 
              disabled={materiAktif.id === 1}
              onClick={() => setMateriAktif(materiReact[materiAktif.id - 2])}
            >
              ← Sebelumnya
            </button>
            <button 
              disabled={materiAktif.id === materiReact.length}
              onClick={() => setMateriAktif(materiReact[materiAktif.id])}
            >
              Selanjutnya →
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;