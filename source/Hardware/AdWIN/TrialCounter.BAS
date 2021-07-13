'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 150000000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Duttlab
'<Header End>
' This Code is used for the Tracking protocol in the PulseShaper app.
' Inputs: par_30 (total count time = no. of samples x count time) (ns)
' Outputs: par_1 (No. of counts per total count time) (#)

' Since the AdWIN has a T11 processor set to high priority, the process time for one instruction is 3.3 ns (refer the documentation)  

#Include ADwinGoldII.inc


init:
  Processdelay = par_30/3.3 
  Cnt_Enable(0)
  Cnt_Clear(1)           ' Clear counter 1
  Cnt_Mode(1,8)          ' Counter input external
  Cnt_Enable(1)         ' enable counter 1

event:
  par_1 = Cnt_Read(1)
  Cnt_Clear(1)

finish:
  Cnt_Enable(0)
