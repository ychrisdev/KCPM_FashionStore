const WalletInfo = () => {
    // Tạm thời comment dòng gọi API lại, dùng dữ liệu cứng để test giao diện
    const wallet = {
        balance: 1000000,
        currency: "VNĐ"
    };

    return (
        <div className="wallet-card" style={{ 
            background: '#1a1a1a', // Màu tối sang trọng
            padding: '20px', 
            borderRadius: '12px', 
            border: '1px solid #333',
            color: '#fff' 
        }}>
            <h3 style={{ color: '#888', fontSize: '14px' }}>SỐ DƯ VÍ</h3>
            <p style={{ fontSize: '32px', fontWeight: 'bold', margin: '10px 0', color: '#ff4d4d' }}>
                {wallet.balance.toLocaleString()} {wallet.currency}
            </p>
            <div style={{ display: 'flex', gap: '10px' }}>
                <button className="btn-deposit">Nạp tiền</button>
            </div>
        </div>
    );
};