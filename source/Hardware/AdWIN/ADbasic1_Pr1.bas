'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 3000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 5.0.8
' Optimize                       = Yes
' Optimize_Level                 = 1
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Kai
'<Header End>
#Include ADwinGoldII.inc

init:
  Cnt_Enable(0)
  Cnt_Mode(2,8)          ' Counter 1 set to increasing
  par_10=0
  Cnt_Clear(2)           ' Clear counter 1
  
event:
  par_1=Read_Timer()
  par_2=Read_Timer()-par_1
  Cnt_Enable(2)          ' enable counter 1
  par_3=Read_Timer()-par_1
  CPU_Sleep(10)          ' count time 300ns
  par_4=Read_Timer()-par_1
  Cnt_Enable(0)          ' disable counter 1
  par_5=Read_Timer()-par_1
  Cnt_Latch(2)        ' accumulate sig
  par_6=Read_Timer()-par_1
  CPU_Sleep(10)         ' reset time 2000ns
  par_7=Read_Timer()-par_1
  Cnt_Enable(2)          ' enable counter 1
  CPU_Sleep(10)          ' count time 300ns
  Cnt_Enable(0)          ' disable counter 1
  
  par_8=Read_Timer()-par_1
  par_19=par_19+Cnt_Read_Latch(2)
  Par_20=par_20+Cnt_Read(2)
  par_21=par_20-par_19
  par_9=Read_Timer()-par_1
  Cnt_Clear(2)           ' Clear counter 1
  Inc(par_10)
  if (par_10=100000) Then
    end
  endif
