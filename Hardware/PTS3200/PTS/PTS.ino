//defines all variables used throughout script
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
   //loops through pins 2-11 and sets them as output pins
   for (i=2;i<12;i++){
       pinMode(i,OUTPUT);
   }
   //loops through pins 22-49 and sets them as output pins
   for (i=22;i<50;i++){
       pinMode(i,OUTPUT);
   }
   //loops through pins 2-11 and puts them on high
   pinMode(LED_BUILTIN,OUTPUT);
   for (ard=2;ard<12;ard++){
       digitalWrite(ard,HIGH);
   }
   //loops through pins 22-49 and sets them to high
   for (ard=22;ard<50;ard++){
        digitalWrite(ard,HIGH);
   }
   //sets built in LED to output
   digitalWrite(LED_BUILTIN,LOW);
   Serial.println("Initialized");


}
//calls different functions based on character input from python script
//either 's' 'f' 'p' or 'b'
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
//prints the current bcd string, corresponds to read function in PTS.ino
void send_current_bcd_string(){
    // will need to implement this
    Serial.println(b);
}

void single_sweep() {
    //takes one query from PTS.py and reads each parameter of the function and saves it to variables to sweep through
    //the given frequency range
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
    //loops through many frequencies within a desired range? Converts to bcd and then sends output to PTS
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
   //resets all pins to default high at end of function
   for (ard=2;ard<12;ard++)
       {digitalWrite(ard,HIGH);}
   for (ard=22;ard<50;ard++)
       {digitalWrite(ard,HIGH);}
   Serial.println("0");

}
//takes single frequency input, converts it to bcd format, then turns off corresponding pins to send to PTS
void single_frequency() {
     freq=Serial.readStringUntil('#');
     //Serial.println(freq);
     incomingByte = freq;
     a="";b="";output="";
     int i;
     //converts freq to bcd
     /*
     for ex: if the first digit is an 8, the function first converts it to binary (1000) the function does nothing because it is
     already 4 digits, therefore in bcd. However, if the incoming digit is 4 for example, 100 in binary, the function adds a 0 to the
     front to make it 4 digits and bcd. 100 goes to 0100.
     */
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
     //turns off arduino pins corresponding to the ones in the freq(bcd), because pts is negative true logic
     for (i=0;i<38;i++){
          if (b[i+2]=='0'){digitalWrite(pin[i],HIGH);}
          else{digitalWrite(pin[i],LOW); output += pin[i]+d;}
         }
     Serial.println("Pins set LOW: " + output);
}
//controls power output, input of this function must be in terms of PWM duty cycle: account for that in python function
void  power_control(){
  power = Serial.readStringUntil('#');
  pw = power.toInt();
  analogWrite(PWMpin,pw);
}


