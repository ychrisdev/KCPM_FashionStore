import { Outlet } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';
import FloatingContactBar from './FloatingContactBar';
import "../styles/components/Layout.css";

export default function Layout() {
  return (
    <div className="layout">
      <Header />
      <main className="main">
        <Outlet />
      </main>
      <Footer />
      <FloatingContactBar />
    </div>
  );
}