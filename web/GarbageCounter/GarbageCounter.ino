int sensorPin_1 = 2;   // 缶センサー
int sensorPin_2 = 4;   // ペットボトルセンサー
int sensorPin_3 = 7;   // 燃えるゴミセンサー


int count_1 = 0;
int count_2 = 0;
int count_3 = 0;


int lastState_1 = HIGH;
int lastState_2 = HIGH;
int lastState_3 = HIGH;



void setup() {

  pinMode(sensorPin_1, INPUT);
  pinMode(sensorPin_2, INPUT);
  pinMode(sensorPin_3, INPUT);


  Serial.begin(9600);

}



void loop() {


  int sensorState_1 = digitalRead(sensorPin_1);
  int sensorState_2 = digitalRead(sensorPin_2);
  int sensorState_3 = digitalRead(sensorPin_3);



  // センサー1
  if(lastState_1 == HIGH && sensorState_1 == LOW){

    count_1++;

    Serial.print("CAN:");
    Serial.println(count_1);

    delay(300);

  }



  // センサー2
  if(lastState_2 == HIGH && sensorState_2 == LOW){

    count_2++;

    Serial.print("PETBOTTLE:");
    Serial.println(count_2);

    delay(300);

  }



  // センサー3
  if(lastState_3 == HIGH && sensorState_3 == LOW){

    count_3++;

    Serial.print("BURNABLE:");
    Serial.println(count_3);

    delay(300);

  }



  lastState_1 = sensorState_1;
  lastState_2 = sensorState_2;
  lastState_3 = sensorState_3;


}
