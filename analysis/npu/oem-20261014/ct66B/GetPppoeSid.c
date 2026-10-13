
bool GetPppoeSid(long param_1,undefined2 *param_2,undefined2 *param_3)

{
  byte bVar1;
  byte *pbVar2;
  
  pbVar2 = *(byte **)(param_1 + 0x188);
  if (5 < DebugLevel) {
    _printk(&DAT_0016c538);
    _printk(&DAT_0016c550,*pbVar2 >> 4);
    _printk(&DAT_0016c560,*pbVar2 & 0xf);
    _printk(&DAT_0016c570,pbVar2[1]);
    _printk(&DAT_0016c580,*(ushort *)(pbVar2 + 2) >> 8 | *(ushort *)(pbVar2 + 2) << 8);
    _printk(&DAT_0016c590,*(ushort *)(pbVar2 + 4) >> 8 | *(ushort *)(pbVar2 + 4) << 8);
    _printk(&DAT_0016c5a0,*(ushort *)(pbVar2 + 6) >> 8 | *(ushort *)(pbVar2 + 6) << 8);
    _printk(&DAT_0016c5b0,*(ushort *)(pbVar2 + 8) >> 8 | *(ushort *)(pbVar2 + 8) << 8);
    _printk(&DAT_0016c5c0);
  }
  *param_3 = *(undefined2 *)(pbVar2 + 6);
  bVar1 = *pbVar2;
  if (bVar1 == 0x11) {
    *param_2 = *(undefined2 *)(pbVar2 + 2);
  }
  return bVar1 != 0x11;
}

