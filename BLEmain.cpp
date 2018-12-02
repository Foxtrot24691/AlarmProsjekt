/* mbed Microcontroller Library
 * Copyright (c) 2006-2013 ARM Limited
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
//komentarene i engelsk er fra BLE lab oppgaven fra EN-SOC faget
//Takk til Lars for mye hjelp med å kombinere tjenestene
//Ett veldig kjapt knappetrykk virker som det regnes som to trykk i noen tilfeller, prøvde å fikse dette, men fikk det ikke til

#include "mbed.h"
#include "ble/BLE.h"
#include "SharedService.h"
//Koden bruker interrupt til å bytte status på LED1, LED1 status blir lest av for å styre alarmens status i python koden
//Setter LED1 til output
DigitalOut BLE_LED(LED1, 0);      

//Erklerer knappen BUTTON1 som input interrupt
//Interrupt gjør koden mer responsiv siden den ikke venter med å reagere på knappetrykket
InterruptIn button(BUTTON1);

//gjenkjennelig navn
const static char     DEVICE_NAME[] = "PI_5";            
static const uint16_t uuid16_list[] = {SharedService::SHARED_SERVICE_UUID};

static SharedService *sharedServicePtr;

//Deklarerer tre tilstander for button og initialiserer som IDLE
enum
{
    RELEASED = 0,
    PRESSED,
    IDLE
};
static uint8_t buttonState = IDLE;


void buttonPressedCallback(void)
{
    /* Note that the buttonPressedCallback() executes in interrupt context, so it is safer to access
     * BLE device API from the main thread. */
    buttonState = PRESSED;
    BLE_LED = !BLE_LED;
}

void buttonReleasedCallback(void)
{
    /* Note that the buttonReleasedCallback() executes in interrupt context, so it is safer to access
     * BLE device API from the main thread. */
    buttonState = RELEASED;
}

/**
 * This callback allows the LEDService to receive updates to the ledState Characteristic.
 *
 * @param[in] params
 *     Information about the characterisitc being updated.
 */
void onDataWrittenCallback(const GattWriteCallbackParams *params) 
{
    if ((params->handle == sharedServicePtr->getValueHandle()) && (params->len == 1)) 
    {      
        BLE_LED = *(params->data);
    }
}

void disconnectionCallback(const Gap::DisconnectionCallbackParams_t *params)
{
    BLE::Instance().gap().startAdvertising();
}

/**
 * This function is called when the ble initialization process has failled
 */
void onBleInitError(BLE &ble, ble_error_t error)
{
    /* Initialization error handling should go here */
}

/**
 * Callback triggered when the ble initialization process has finished
 */
void bleInitComplete(BLE::InitializationCompleteCallbackContext *params)
{
    BLE&        ble   = params->ble;
    ble_error_t error = params->error;

    if (error != BLE_ERROR_NONE) 
    {
        /* In case of error, forward the error handling to onBleInitError */
        onBleInitError(ble, error);
        return;
    }

    /* Ensure that it is the default instance of BLE */
    if(ble.getInstanceID() != BLE::DEFAULT_INSTANCE) 
    {
        return;
    }

    ble.gap().onDisconnection(disconnectionCallback);
    ble.gattServer().onDataWritten(onDataWrittenCallback);

    /* Setup primary service */
    //ledServicePtr = new DualService(ble, false, false /* initial value for button pressed */);
    bool initialValueForLEDCharacteristic = false;
    sharedServicePtr = new SharedService(ble, false, initialValueForLEDCharacteristic /* initial values for LED and button */);

    /* setup advertising */
    ble.gap().accumulateAdvertisingPayload(GapAdvertisingData::BREDR_NOT_SUPPORTED | GapAdvertisingData::LE_GENERAL_DISCOVERABLE);
    
    ble.gap().accumulateAdvertisingPayload(GapAdvertisingData::COMPLETE_LIST_16BIT_SERVICE_IDS, (uint8_t *)uuid16_list, sizeof(uuid16_list));
    ble.gap().accumulateAdvertisingPayload(GapAdvertisingData::COMPLETE_LOCAL_NAME, (uint8_t *)DEVICE_NAME, sizeof(DEVICE_NAME));

    ble.gap().setAdvertisingType(GapAdvertisingParams::ADV_CONNECTABLE_UNDIRECTED);
    ble.gap().setAdvertisingInterval(500); /* 1000ms. */
    ble.gap().startAdvertising();
}

int main(void)
{
    button.fall(buttonPressedCallback);  //buttonPressedCallback kalles når knappen trykkes (fallende flanke)
    button.rise(buttonReleasedCallback); //buttonReleasedCallback kalles når knappen trykkes (fallende flanke)
    
    BLE &ble = BLE::Instance();
    ble.init(bleInitComplete);
    
    /* SpinWait for initialization to complete. This is necessary because the
     * BLE object is used in the main loop below. */
    while (ble.hasInitialized()  == false) { /* spin loop */ }
    
    while (true)
    {
        if (buttonState != IDLE)   
        {
            sharedServicePtr->updateButtonState(buttonState);
            sharedServicePtr->updateLedState(BLE_LED);
            buttonState = IDLE;
        }
        ble.waitForEvent();        //Oppdaterer LED på HR1017 når knapp trykkes eller når Pi-bryter sender signal
    }
}
