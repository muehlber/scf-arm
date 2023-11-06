static int v;

int main(int a, int b)
{
  int result = 3;

  if (a < b)
  {
    result = 7;
  }
  /* Secret-dependent branch because result was assigned in a statement
   *  that is control-dependent on another secret-dependent branch.
   */
  if (result == b) 
  {
    v++;
  }

  return result;
}
