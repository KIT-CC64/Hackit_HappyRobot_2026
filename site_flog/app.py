from flask import Flask, jsonify
from flask_cors import CORS
import serial
import threading


app = Flask(__name__)
CORS(app)


# Arduinoのポート
# Windowsの場合 COM3, COM4など
arduino = serial.Serial(
    "COM4",
    9600,
    timeout=1
)


# カウント保存
data = {
    "counts":{
        "can":0,
        "petbottle":0,
        "burnable":0
    },
    "hunger":0,
    "level":1,
    "stage":"otamajakushi"
}



# Arduino読み取り
def read_arduino():

    while True:

        line = arduino.readline().decode().strip()


        if line:

            print(line)


            if line.startswith("CAN:"):

                data["counts"]["can"] = int(
                    line.replace("CAN:","")
                )


            elif line.startswith("PETBOTTLE:"):

                data["counts"]["petbottle"] = int(
                    line.replace("PETBOTTLE:","")
                )


            elif line.startswith("BURNABLE:"):

                data["counts"]["burnable"] = int(
                    line.replace("BURNABLE:","")
                )



# 別スレッドでArduino監視
threading.Thread(
    target=read_arduino,
    daemon=True
).start()



# Web API
@app.route("/api/status")
def status():

    return jsonify(data)



if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )