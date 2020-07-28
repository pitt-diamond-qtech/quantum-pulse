
String Start;
String Stop;
String Steps;
String Dwell_Time;

float A;
float B;
float t;
int s;

String Mode;
String incomingByte; // for incoming serial data
String a;
String digit;
String b;
String output;
String d=", ";
int pin[38]={3,2,7,6,5,4,11,10,9,8,25,24,23,22,29,28,27,26,33,32,31,30,37,36,35,34,41,40,39,38,45,44,43,42,49,48,47,46};
int PWMpin = 12;
int pw;
String power;
int m=0;
int n=5;
String freq;
int ard;
int str;

char user_input;

void setup() {
   Serial.begin(9600);     // opens serial port, sets data rate to 9600 bps
   int i,ard,str;
   for (i=2;i<12;i++){
       pinMode(i,OUTPUT);
   }
   for (i=22;i<50;i++){
       pinMode(i,OUTPUT);
   }
   pinMode(LED_BUILTIN,OUTPUT);
   for (ard=2;ard<12;ard++){
       digitalWrite(ard,HIGH);
   }
   for (ard=22;ard<50;ard++){
        digitalWrite(ard,HIGH);
   }
   digitalWrite(LED_BUILTIN,LOW);
   Serial.println("Initialized");


}

void loop() {
    user_input = Serial.read();
    if (user_input == 's'){
      single_sweep();
    }
    if (user_input == 'f'){
      single_frequency();
    }
    if (user_input == 'p'){
      power_control();
      }
    if (user_input == 'b'){
        send_current_bcd_string();
    }
}

void send_current_bcd_string(){
    // will need to implement this
    Serial.println(b);
}

void single_sweep() {

    //Serial.println("single_sweep");
    Start=Serial.readStringUntil('#');
    A=Start.toFloat();
    Stop=Serial.readStringUntil('#');
    B=Stop.toFloat();
    Steps=Serial.readStringUntil('#');
    s=Steps.toInt();
    Dwell_Time=Serial.readStringUntil('#');
    t=Dwell_Time.toFloat();
    Serial.println(A);
    Serial.println(B);
    Serial.println(s);
    Serial.println(t);
    // read the incoming byte:
    int k;int p;

    for (k=0;k<s+1;k++){
         freq=String(k*(B-A)/s+A);
         //Serial.println(freq);
         incomingByte = freq;
         a="";b="";output="";
         int i;
         for (i=0;i<10;i++){
              digit = String(incomingByte[i]);
              //Serial.println(digit);
              a=String(digit.toInt(),BIN);
              if (a.length()==3){
                  a=String(0,BIN)+a;}
              if (a.length()==2){
                  a=String(0,BIN)+String(0,BIN)+a;}
              if (a.length()==1){
                  a=String(0,BIN)+String(0,BIN)+String(0,BIN)+a;}
               b+=a;
              }
         for (i=0;i<38;i++){
              if (b[i+2]=='0'){digitalWrite(pin[i],HIGH);}
              else{digitalWrite(pin[i],LOW); output += pin[i]+d;}
             }
         digitalWrite(LED_BUILTIN,HIGH);
         delay(t);
         digitalWrite(LED_BUILTIN,LOW);
         delay(t);

         }
   for (ard=2;ard<12;ard++)
       {digitalWrite(ard,HIGH);}
   for (ard=22;ard<50;ard++)
       {digitalWrite(ard,HIGH);}
   Serial.println("0");

}

void single_frequency() {
     freq=Serial.readStringUntil('#');
     //Serial.println(freq);
     incomingByte = freq;
     a="";b="";output="";
     int i;
     for (i=0;i<10;i++){
          digit = String(incomingByte[i]);
          //Serial.println(digit);
          a=String(digit.toInt(),BIN);
          if (a.length()==3){
              a=String(0,BIN)+a;}
          if (a.length()==2){
              a=String(0,BIN)+String(0,BIN)+a;}
          if (a.length()==1){
              a=String(0,BIN)+String(0,BIN)+String(0,BIN)+a;}
           b+=a;
          }
     for (i=0;i<38;i++){
          if (b[i+2]=='0'){digitalWrite(pin[i],HIGH);}
          else{digitalWrite(pin[i],LOW); output += pin[i]+d;}
         }
     Serial.println("Pins set LOW: " + output);
}

void  power_control(){
  power = Serial.readStringUntil('#');
  pw = power.toInt();
  analogWrite(PWMpin,pw);
}


