int sensorPin = 2;   // 赤外線センサーをつなぐピン
int count = 0;       // カウント数
int lastState = HIGH;

void setup() {
  pinMode(sensorPin, INPUT);
  Serial.begin(9600);
}

void loop() {
  int sensorState = digitalRead(sensorPin);

  // センサーが遮られた瞬間を検出
  if (lastState == HIGH && sensorState == LOW) {
    count++;
    Serial.print("Count: ");
    Serial.println(count);
    delay(300); // 誤カウント防止
  }

  lastState = sensorState;
}
