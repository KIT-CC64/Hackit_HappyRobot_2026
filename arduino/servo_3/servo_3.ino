#include <Servo.h>

Servo servos[3];

const int servoPins[3] = {9, 10, 11};

// 口ごとの開く角度
const int openAngle[3] = {
  180,  // 口1
  180,   // 口2
  180    // 口3
};

// 状態管理
bool moving[3] = {false, false, false};
unsigned long openTime[3];
const unsigned long OPEN_TIME = 3000;   // 3秒後に閉じる

void setup() {
  Serial.begin(9600);

  for (int i = 0; i < 3; i++) {
    servos[i].attach(servoPins[i]);
    servos[i].write(0);   // 初期位置(閉)
  }
}

void loop() {

  // シリアル受信
  if (Serial.available()) {
    int servoNum = Serial.parseInt();

    // 4のとき
    if (servoNum == 4) {
      for (int i = 0; i < 3; i++) {
        servos[i].write(openAngle[i]);
        moving[i] = false;   // 自動で閉じない
      }

      Serial.println("END");
      while (true);          // プログラム停止
    }

    // 1～3のとき
    if (servoNum >= 1 && servoNum <= 3) {
      openLid(servoNum, openAngle[servoNum - 1]);
    }
  }

  // 一定時間後に閉じる
  for (int i = 0; i < 3; i++) {
    if (moving[i] && millis() - openTime[i] >= OPEN_TIME) {
      servos[i].write(0);    // 閉じる
      moving[i] = false;
    }
  }
}

void openLid(int servoNum, int angle) {

  int index = servoNum - 1;

  servos[index].write(angle);   // 開く

  moving[index] = true;
  openTime[index] = millis();
}