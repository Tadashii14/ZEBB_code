/* zfish_controller.ino
   Arduino UNO firmware for zebrafish rig control
   - MOSFET PWM outputs for IR (D3), PUMP (D5), VIB (D6)
   - Relays for WHITE (D7) and HEATER (D8)
   - DS18B20 on D2
   - Serial protocol: text commands
*/
#include <OneWire.h>
#include <DallasTemperature.h>

#define PIN_IR_PWM    3   // Timer2, PWM
#define PIN_PUMP_PWM  5   // Timer0, PWM
#define PIN_VIB_PWM   6   // Timer0, PWM

#define PIN_RELAY_WHITE 7
#define PIN_RELAY_HEATER 8

#define PIN_DS18B20 2

OneWire oneWire(PIN_DS18B20);
DallasTemperature sensors(&oneWire);

// Experiment state
bool experimentRunning = false;
unsigned long experimentStartMillis = 0;
unsigned long experimentDurationMs = 0; // in ms

// Stimulus pattern (simple)
struct Stimulus {
  bool useIR;
  bool useWhite;
  bool usePump;
  bool useVib;
  bool useHeater;
  unsigned long onMs;
  unsigned long offMs;
  int irPWM;   // 0-255
  int pumpPWM; // 0-255
  int vibPWM;  // 0-255
};

Stimulus currentPattern = {true, false, false, false, false, 1000, 1000, 200, 200, 128};
unsigned long nextStimToggle = 0;
bool stimIsOn = false;

// safety
float maxTempC = 50.0;
unsigned long lastTempReport = 0;
const unsigned long TEMP_REPORT_INTERVAL = 2000; // ms

// helpers for serial parsing
String inputLine = "";

void setup() {
  Serial.begin(115200);
  sensors.begin();

  pinMode(PIN_IR_PWM, OUTPUT);
  pinMode(PIN_PUMP_PWM, OUTPUT);
  pinMode(PIN_VIB_PWM, OUTPUT);
  pinMode(PIN_RELAY_WHITE, OUTPUT);
  pinMode(PIN_RELAY_HEATER, OUTPUT);

  // safe defaults
  analogWrite(PIN_IR_PWM, 0);
  analogWrite(PIN_PUMP_PWM, 0);
  analogWrite(PIN_VIB_PWM, 0);
  digitalWrite(PIN_RELAY_WHITE, LOW);
  digitalWrite(PIN_RELAY_HEATER, LOW);

  Serial.println("ZFISHCTRL READY");
  advertiseStatus();
}

void loop() {
  // read serial
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      inputLine.trim();
      if (inputLine.length() > 0) handleCommand(inputLine);
      inputLine = "";
    } else if (c >= 32) {
      inputLine += c;
    }
  }

  // report temperature occasionally
  if (millis() - lastTempReport > TEMP_REPORT_INTERVAL) {
    sensors.requestTemperatures();
    float t = sensors.getTempCByIndex(0);
    Serial.print("TEMP ");
    Serial.println(t);
    lastTempReport = millis();
    if (!isnan(t) && t > maxTempC) {
      // emergency stop heater
      digitalWrite(PIN_RELAY_HEATER, LOW);
      Serial.println("EMERGENCY TEMP_OVER");
      // optionally stop experiment
      stopExperiment();
    }
  }

  // experiment runner
  if (experimentRunning) {
    unsigned long now = millis();
    if (experimentDurationMs > 0 && now - experimentStartMillis >= experimentDurationMs) {
      stopExperiment();
      Serial.println("EXPERIMENT_FINISHED");
    } else {
      // run stimulus toggle pattern
      if (now >= nextStimToggle) {
        if (stimIsOn) {
          // turn stim off
          applyStimulus(false);
          stimIsOn = false;
          nextStimToggle = now + currentPattern.offMs;
        } else {
          // turn stim on
          applyStimulus(true);
          stimIsOn = true;
          nextStimToggle = now + currentPattern.onMs;
        }
        // log
        Serial.print("STIM_TOGGLE ");
        Serial.println(stimIsOn ? "ON" : "OFF");
      }
    }
  }
}

// apply stimulus: set outputs
void applyStimulus(bool on) {
  if (on) {
    if (currentPattern.useIR) analogWrite(PIN_IR_PWM, currentPattern.irPWM); else analogWrite(PIN_IR_PWM, 0);
    if (currentPattern.usePump) analogWrite(PIN_PUMP_PWM, currentPattern.pumpPWM); else analogWrite(PIN_PUMP_PWM, 0);
    if (currentPattern.useVib) analogWrite(PIN_VIB_PWM, currentPattern.vibPWM); else analogWrite(PIN_VIB_PWM, 0);
    if (currentPattern.useWhite) digitalWrite(PIN_RELAY_WHITE, HIGH); else digitalWrite(PIN_RELAY_WHITE, LOW);
    if (currentPattern.useHeater) digitalWrite(PIN_RELAY_HEATER, HIGH); else digitalWrite(PIN_RELAY_HEATER, LOW);
  } else {
    // everything off
    analogWrite(PIN_IR_PWM, 0);
    analogWrite(PIN_PUMP_PWM, 0);
    analogWrite(PIN_VIB_PWM, 0);
    digitalWrite(PIN_RELAY_WHITE, LOW);
    digitalWrite(PIN_RELAY_HEATER, LOW);
  }
}

void handleCommand(String &cmd) {
  cmd.toUpperCase();
  Serial.print("CMD:");
  Serial.println(cmd);
  if (cmd.startsWith("START")) {
    // optional args: START DURATION_MS
    unsigned long dur = 0;
    int sp = cmd.indexOf(' ');
    if (sp > 0) dur = (unsigned long) cmd.substring(sp + 1).toInt();
    startExperiment(dur);
  } else if (cmd.startsWith("STOP")) {
    stopExperiment();
  } else if (cmd.startsWith("SET ")) {
    // example: SET IR 200  or SET PATTERN IR+PUMP+VIB 1000 1000 200 200 128
    if (cmd.indexOf("IR ") > 0) {
      int v = cmd.substring(cmd.indexOf("IR ") + 3).toInt();
      v = constrain(v, 0, 255);
      currentPattern.irPWM = v;
      Serial.print("SET IR PWM ");
      Serial.println(v);
    } else if (cmd.indexOf("PUMP ") > 0) {
      int v = cmd.substring(cmd.indexOf("PUMP ") + 5).toInt();
      v = constrain(v, 0, 255);
      currentPattern.pumpPWM = v;
      Serial.print("SET PUMP PWM ");
      Serial.println(v);
    } else if (cmd.indexOf("VIB ") > 0) {
      int v = cmd.substring(cmd.indexOf("VIB ") + 4).toInt();
      v = constrain(v, 0, 255);
      currentPattern.vibPWM = v;
      Serial.print("SET VIB PWM ");
      Serial.println(v);
    } else if (cmd.indexOf("PATTERN ") > 0) {
      String tail = cmd.substring(cmd.indexOf("PATTERN ") + 8);
      int i1 = tail.indexOf(' ');
      if (i1 > 0) {
        String targets = tail.substring(0, i1);
        currentPattern.useIR = targets.indexOf("IR") >= 0;
        currentPattern.useWhite = targets.indexOf("WHITE") >= 0;
        currentPattern.usePump = targets.indexOf("PUMP") >= 0;
        currentPattern.useVib = targets.indexOf("VIB") >= 0;
        String nums = tail.substring(i1 + 1);
        int tks[6] = {0,0,0,0,0,0};
        int tk = 0;
        while (tk < 6) {
          int sp = nums.indexOf(' ');
          if (sp < 0) {
            if (nums.length() > 0) tks[tk++] = nums.toInt();
            break;
          } else {
            tks[tk++] = nums.substring(0, sp).toInt();
            nums = nums.substring(sp + 1);
          }
        }
        if (tks[0] > 0) currentPattern.onMs = (unsigned long)tks[0];
        if (tks[1] > 0) currentPattern.offMs = (unsigned long)tks[1];
        if (tks[2] > 0) currentPattern.irPWM = constrain(tks[2], 0, 255);
        if (tks[3] > 0) currentPattern.pumpPWM = constrain(tks[3], 0, 255);
        if (tks[4] > 0) currentPattern.vibPWM = constrain(tks[4], 0, 255);
        Serial.println("PATTERN SET");
      }
    }
  } else if (cmd == "STATUS") {
    advertiseStatus();
  } else if (cmd == "TEMP?") {
    sensors.requestTemperatures();
    Serial.print("TEMP ");
    Serial.println(sensors.getTempCByIndex(0));
  } else if (cmd.startsWith("MANUAL ")) {
    if (cmd.indexOf("IR ") > 0) {
      int v = cmd.substring(cmd.indexOf("IR ") + 3).toInt();
      analogWrite(PIN_IR_PWM, constrain(v,0,255));
      Serial.println("MANUAL_IR_SET");
    } else if (cmd.indexOf("WHITE ON") > 0) {
      digitalWrite(PIN_RELAY_WHITE, HIGH);
    } else if (cmd.indexOf("WHITE OFF") > 0) {
      digitalWrite(PIN_RELAY_WHITE, LOW);
    } else if (cmd.indexOf("HEATER ON") > 0) {
      digitalWrite(PIN_RELAY_HEATER, HIGH);
    } else if (cmd.indexOf("HEATER OFF") > 0) {
      digitalWrite(PIN_RELAY_HEATER, LOW);
    } else if (cmd.indexOf("PUMP ") > 0) {
      int v = cmd.substring(cmd.indexOf("PUMP ") + 5).toInt();
      analogWrite(PIN_PUMP_PWM, constrain(v,0,255));
    } else if (cmd.indexOf("VIB ") > 0) {
      int v = cmd.substring(cmd.indexOf("VIB ") + 4).toInt();
      analogWrite(PIN_VIB_PWM, constrain(v,0,255));
    }
  }
}

void startExperiment(unsigned long durationMs) {
  if (experimentRunning) {
    Serial.println("ALREADY_RUNNING");
    return;
  }
  experimentRunning = true;
  experimentStartMillis = millis();
  experimentDurationMs = durationMs;
  stimIsOn = false;
  nextStimToggle = millis(); // toggle immediately to start pattern
  Serial.println("EXPERIMENT_STARTED");
}

void stopExperiment() {
  experimentRunning = false;
  experimentDurationMs = 0;
  applyStimulus(false);
  Serial.println("EXPERIMENT_STOPPED");
}

void advertiseStatus() {
  Serial.print("STATUS RUNNING:");
  Serial.print(experimentRunning ? "1" : "0");
  Serial.print(" DURATION_MS:");
  Serial.print(experimentDurationMs);
  Serial.print(" IR_PWM:");
  Serial.print(currentPattern.irPWM);
  Serial.print(" PUMP_PWM:");
  Serial.print(currentPattern.pumpPWM);
  Serial.print(" VIB_PWM:");
  Serial.print(currentPattern.vibPWM);
  Serial.print(" PAT_ON:");
  Serial.print(currentPattern.onMs);
  Serial.print(" PAT_OFF:");
  Serial.println(currentPattern.offMs);
}
