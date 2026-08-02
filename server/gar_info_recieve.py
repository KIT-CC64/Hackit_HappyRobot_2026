# 【参考コード・未使用】
# 実際にArduino(GarbageCounter.ino)が送ってくるのは PASS1/PASS2/PASS3 ではなく
# CAN: / PETBOTTLE: / BURNABLE: 形式（server/sensor_bridge.py が実際の受信処理）。
# こちらは初期検討時のイメージ用スニペットとして残しています。

# Python側（受信用イメージ）
line = ser.readline().decode("utf-8").strip()

if line == "PASS1":
    # 口1（ペットボトル）のカウントを増やすため Flask API を呼び出す
    requests.post(
        "http://localhost:5000/api/feed", json={"type": "petbottle"}
    )
elif line == "PASS2":
    # 口2（缶）のカウントを増やす
    requests.post("http://localhost:5000/api/feed", json={"type": "can"})

elif line == "PASS3":
    # 口3（燃えるゴミ）のカウントを増やす
    requests.post("http://localhost:5000/api/feed", json={"type": "burnable"})