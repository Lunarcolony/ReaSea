export function FeedSkeleton() {
  return (
    <div className="home">
      <div className="hero skeleton-block skeleton-hero" />
      {[1, 2, 3].map((i) => (
        <div key={i} className="feed-row">
          <div className="skeleton-block skeleton-title" />
          <div className="row-scroll">
            {[1, 2, 3, 4].map((j) => (
              <div key={j} className="paper-card skeleton-block skeleton-card" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
