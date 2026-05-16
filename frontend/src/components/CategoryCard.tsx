import { Link } from 'react-router-dom';
import type { Category } from '../types';
import '../styles/components/CategoryCard.css';

interface CategoryCardProps {
  category: Category;
}

export default function CategoryCard({ category }: CategoryCardProps) {
  return (
    <Link to={`/products?category=${category.id}`} className="categoryCard">
      <div className="categoryCardImageWrapper">
        <img src={category.image} alt={category.name} className="categoryCardImage" />
        <div className="categoryCardOverlay">
          <span className="categoryCardView">Xem ngay</span>
        </div>
      </div>
      <div className="categoryCardContent">
        <h3 className="categoryCardName">{category.name}</h3>
        <p className="categoryCardDesc">{category.description}</p>
      </div>
    </Link>
  );
}
