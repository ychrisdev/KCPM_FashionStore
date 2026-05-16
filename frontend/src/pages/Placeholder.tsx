import '../styles/pages/Placeholder.css';
import { Link } from 'react-router-dom';

interface PlaceholderProps {
  icon: string;
  title: string;
  desc: string;
  backLabel?: string;
  backTo?: string;
}

/**
 * Placeholder — reusable "coming soon" page shell for Cart, Login, ProductDetail.
 */
export default function Placeholder({
  icon,
  title,
  desc,
  backLabel = 'Back to Home',
  backTo = '/',
}: PlaceholderProps) {
  return (
    <div className="container">
      <div className="icon">{icon}</div>

      <h1 className="title">
        {title}
      </h1>

      <p className="desc">
        {desc}
      </p>

      <Link to={backTo} className="btn">
        {backLabel}
      </Link>
    </div>
  );
}