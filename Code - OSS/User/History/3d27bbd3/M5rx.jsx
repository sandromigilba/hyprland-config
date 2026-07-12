// src/App.jsx
import { useState } from 'react';
import { materiReact } from './data/materi'; // Pastikan data materi Anda sesuai
import './App.css';

function App() {
  // State untuk menyimpan materi yang sedang aktif dipilih user
  const [materiAktif, setMateriAktif] = useState(materiReact[0]);

  // Helper function untuk navigasi materi
  const handleNavigasi = (arah) => {
    const currentIndex = materiReact.findIndex(m => m.id === materiAktif.id);
    let nextIndex;

    if (arah === 'prev' && currentIndex > 0) {
      nextIndex = currentIndex - 1;
    } else if (arah === 'next' && currentIndex < materiReact.length - 1) {
      nextIndex = currentIndex + 1;
    } else {
      return; // Tidak ada navigasi
    }

    setMateriAktif(materiReact[nextIndex]);
  };

  return (
    <div className="firebug-platform">
      <div className="main-viewport">
        
        {/* Header Utama (Rounded Box) */}
        <header className="main-header-box rounded-box">
          <h2>🚀 KelasCoding: Belajar React v19</h2>
        </header>

        <div className="layout-split">
          
          {/* Sidebar Materi (Rounded Box) */}
          <aside className="materi-sidebar-box rounded-box">
            <h3>Materi</h3>
            <ul className="materi-list">
              {materiReact.map((materi, index) => (
                <li key={materi.id}>
                  <button 
                    className={`materi-item-btn rounded-box ${materiAktif.id === materi.id ? 'active' : ''}`}
                    onClick={() => setMateriAktif(materi)}
                  >
                    Materi {index + 1}. {materi.judul}
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          {/* Konten Utama */}
          <main className="content-area-main">
            
            {/* 1. Kotak Deskripsi Materi (Rounded Box) */}
            <div className="content-description-box rounded-box">
              <h1>{materiAktif.judul}</h1>
              <p className="penjelasan monospace-text">
                {/* Gunakan data asli jika ada, jika tidak pakai placeholder dari gambar */}
                {materiAktif.konten || `React yang memmciatan sesamah Havin, nehampat mangan using attu komponen contoh.`}
              </p>
            </div>

            {/* 2. Kotak Contoh Kode (Rounded Box) */}
            <div className="content-code-box rounded-box">
              <h4>Contoh Komponen Sederhana</h4>
              <div className="inner-code-window rounded-box">
                <pre>
                  <code>
                    {/* Syntax highlighting harus dikelola secara manual atau via library lain, 
                        di sini kita asumsikan data sudah berformat atau pakai placeholder gambar */}
                    <span className="tokyo-keyword">function</span> <span className="tokyo-function">Hello</span>() {'{'}<br/>
                    &nbsp;&nbsp;<span className="tokyo-keyword">return</span> <span className="tokyo-tag">&lt;h1&gt;</span>Halo Dunia!<span className="tokyo-tag">&lt;h1&gt;</span>;<br/>
                    {'}'}
                  </code>
                </pre>
              </div>
            </div>

            {/* 3. Kotak Navigasi (Rounded Box) */}
            <div className="content-navigation-box rounded-box">
              <button 
                className="nav-btn prev rounded-box" 
                disabled={materiAktif.id === 1}
                onClick={() => handleNavigasi('prev')}
              >
                Sebelumnya
              </button>
              <button 
                className="nav-btn next rounded-box" 
                disabled={materiAktif.id === materiReact.length}
                onClick={() => handleNavigasi('next')}
              >
                Selanjutnya
              </button>
            </div>

          </main>
        </div>
      </div>
    </div>
  );
}

export default App;