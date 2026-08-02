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