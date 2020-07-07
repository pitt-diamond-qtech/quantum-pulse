'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 2
' Initial_Processdelay           = 4000
' Eventsource                    = External
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 5.0.8
' Optimize                       = Yes
' Optimize_Level                 = 1
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Kai
'<Header End>
' 1D_Scan.bas
' Configured as Process 2, Priority High, External trigger.


#Include ADwinGoldII.inc
DIM Data_1[1000] AS LONG
DIM index AS LONG


init:
  Cnt_Enable(0)
  Cnt_Mode(1,8)          ' Counter 1 set to increasing
  Cnt_Enable(1)          ' enable counter 1
  Cnt_Clear(1)           ' Clear counter 1
  index=0


event:
  IF (index>0) THEN
    Data_1[index]=Cnt_Read(1)
  ENDIF
  Cnt_Clear(1)
  Inc(index)


finish:
  Cnt_Enable(0)
