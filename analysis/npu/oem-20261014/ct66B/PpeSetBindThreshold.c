
undefined8 PpeSetBindThreshold(undefined4 param_1)

{
  int iVar1;
  
  set_frame_engine_data(0xbfb50e28,param_1);
  iVar1 = GET_HIR();
  if (iVar1 == 0xe) {
    set_frame_engine_data(0xbfb51e28,param_1);
  }
  RegModifyBits(0xbfb50e28,param_1,0x10);
  iVar1 = GET_HIR();
  if (iVar1 != 0xe) {
    return 0;
  }
  RegModifyBits(0xbfb51e28,param_1,0x10);
  return 0;
}

